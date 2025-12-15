from datetime import datetime, timezone

from bson import ObjectId

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from flask import request, jsonify, Blueprint
metrics_api = Blueprint("metrics_api", __name__)

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('../apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('metrics_api')
logger.setLevel(logging.INFO)

@metrics_api.route('/api/metrics', methods=['POST'])
def save_metrics():
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    logger.info(f"data: {data}")
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        result = mongo.metrics_collection.insert_many(util.camel_to_snake_key(util.fix_datetime(util.remove_id_key(data))))
        inserted_ids = util.objectid_to_str(result.inserted_ids)
        logger.info(f"Successfully saved metrics with IDs: {result.inserted_ids}")

        data_type_id = data[0]['dataTypeId']
        mongo.data_types_collection.update_one({"_id": ObjectId(data_type_id)}, {'$set': {'updated_at': datetime.now(timezone.utc)}})

        return jsonify({'message': 'Data saved successfully', 'data': inserted_ids}), 201
    except Exception as e:
        logger.error(f"Failed to save metrics: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

@metrics_api.route('/api/metrics/<beehive_id>/<data_capture>', methods=['GET'])
def get_metrics(beehive_id, data_capture):
    try:
        sensors = list(mongo.sensors_collection.find({ "beehive_id": beehive_id, "data_capture": data_capture}))
        data_type = mongo.data_types_collection.find_one({"sensor_id": util.objectid_to_str(sensors[0]["_id"]), "data_type": data_capture})
        data_type_id = util.objectid_to_str(data_type["_id"])

        pipeline = [
            # Start with a single document to generate buckets from
            {"$limit": 1},
            {"$addFields": {"now": {"$toDate": "$$NOW"}}},
            # Create array of hour indices (0 to 24)
            {"$addFields": {"hour_indices": {"$range": [0, 25]}}},
            # Unwind the array to create one doc per hour bucket
            {"$unwind": {"path": "$hour_indices"}},
            {"$addFields": {
                "hour_bucket": {
                    "$dateTrunc": {  # Truncate to start of hour for consistent bucketing
                        "date": {
                            "$dateSubtract": {
                                "startDate": "$now",
                                "unit": "hour",
                                "amount": "$hour_indices"
                            }
                        },
                        "unit": "hour",
                        "timezone": "UTC"
                    }
                },
                "time_num": "$hour_indices"
            }},
            {"$sort": {"time_num": -1}},  # Descending: 24hr (oldest) to 0hr (newest)
            # Lookup hourly average value data for each bucket
            {"$lookup": {
                "from": "metrics",
                "let": {"hb": "$hour_bucket", "now": "$now"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": [data_type_id, "$data_type_id"]},  # Exact match on string data_type_id
                                {"$gte": ["$datetime",
                                          {"$dateSubtract": {"startDate": "$$now", "unit": "hour", "amount": 24}}]},
                                {"$eq": [{"$dateTrunc": {"date": "$datetime", "unit": "hour", "timezone": "UTC"}},
                                         "$$hb"]}
                            ]
                        }
                    }},
                    # No parsing needed: Use direct 'value' field (numeric)
                    {"$group": {
                        "_id": None,
                        "avg_value": {"$avg": "$value"}  # Direct average on 'value' field
                    }}
                ],
                "as": "avg_data"
            }},
            # Extract average (default to null if no data)
            {"$addFields": {
                "avg_value": {"$ifNull": [{"$arrayElemAt": ["$avg_data.avg_value", 0]}, None]}
            }},
            # Format output
            {"$addFields": {
                "value": {"$round": ["$avg_value", 1]},
                "time": {"$concat": [{"$toString": "$time_num"}, "hr"]}
            }},
            # Final projection: Use only inclusions to avoid mix of 0/1
            {"$project": {
                "_id": 0,
                "time": 1,
                "value": 1
            }}
        ]

        metrics = util.snake_to_camel_key(util.objectid_to_str(list(mongo.metrics_collection.aggregate(pipeline))))
        logger.info(f'data: {metrics}')
        return jsonify({'data': metrics}), 200
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        return jsonify({'error': f'Failed to get metrics: {str(e)}'}), 500