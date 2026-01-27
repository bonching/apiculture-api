import sys
import traceback
from datetime import datetime, timezone

from bson import ObjectId

from apiculture_api.alerts_api import enqueue_sse
from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from apiculture_api.ai.anomaly_detector import AnomalyDetector
anomaly_detector = AnomalyDetector()

from flask import request, jsonify, Blueprint
metrics_api = Blueprint("metrics_api", __name__)

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

# Force stdout to UTF-8 on Windows (only if not already configured)
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        except (AttributeError, ValueError):
            pass # Already wrapped or not available
    if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding.lower() != 'utf-8':
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
        except (AttributeError, ValueError):
            pass # Already wrapped or not available

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../apiculture-api.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    encoding='utf-8'
)
logger = logging.getLogger('metrics_api')
logger.setLevel(logging.INFO)

@metrics_api.route('/api/metrics', methods=['POST'])
def _save_metrics():
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    return save_metrics(data)

def save_metrics(data):
    logger.info(f"data: {data}")
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        result = mongo.metrics_collection.insert_many(util.camel_to_snake_key(util.fix_datetime(util.remove_id_key(data))))
        inserted_ids = util.objectid_to_str(result.inserted_ids)
        logger.info(f"Successfully saved metrics with IDs: {result.inserted_ids}")

        data_type_id = data[0]['dataTypeId']

        data_type = mongo.data_types_collection.find_one({"_id": ObjectId(data_type_id)})
        if data_type and data_type.get('data_type') == 'honey_harvested':
            honey_value = data[0].get('value', 0)
            honey_unit = data_type.get('unit', 'g')
            image_id = data[0].get('imageId')
            beehive_id = data[0].get('beehiveId')

            # Derive beehiveName and farmName from beehiveId
            beehive_name = None
            farm_name = None
            farm_id = None

            message = f'New honey harvest recorded: {honey_value}{honey_unit}'
            if beehive_id:
                hive = mongo.hives_collection.find_one({"_id": ObjectId(beehive_id)})
                if hive:
                    beehive_name = hive.get('name', 'Unknown Hive')
                    farm = hive.get('farm_id')

                    # Get farm name from farm_id
                    if farm_id:
                        farm = mongo.hives_collection.find_one({"_id": ObjectId(farm_id)})
                        if farm:
                            farm_name = farm.get('name', 'Unknown Farm')

                    # Build detailed message
                    if farm_name:
                        message = f'New honey harvest from {beehive_name} at {farm_name}: {honey_value}{honey_unit}'
                    else:
                        message = f'New honey harvest from {beehive_name}: {honey_value}{honey_unit}'

            alert_event = {
                'title': 'Honey Harvested',
                'message': message,
                'severity': 'info',
                'imageId': image_id,
                'beehiveId': beehive_id,
                'beehiveName': beehive_name,
                'farm_id': util.objectid_to_str(farm_id) if farm_id else None,
                'farm_name': farm_name,
                'dataType': "honey_harvested",
                'alertType': "honey_harvested",
                'sensorValue': honey_value
            }
            enqueue_sse(alert_event)
            logger.info(f"Enqueued honey harvest alert: {message}")

        mongo.data_types_collection.update_one({"_id": ObjectId(data_type_id)}, {'$set': {'updated_at': datetime.now(timezone.utc)}})

        for metric in data:
            anomaly_detector.check_anomaly(metric)

        return jsonify({'message': 'Data saved successfully', 'data': inserted_ids}), 201
    except Exception as e:
        logger.error(f"Failed to save metrics: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

@metrics_api.route('/api/metrics/<beehive_id>/<data_capture>', methods=['GET'])
def get_metrics(beehive_id, data_capture):
    try:
        sensors = list(mongo.sensors_collection.find({ "beehive_id": beehive_id, "data_capture": util.camel_to_snake(data_capture)}))

        # Return empty data if no sensors found
        if not sensors:
            logger.warning(f"No sensors found for beehive_id: {beehive_id}, data_capture: {data_capture}")
            return jsonify({'data': []}), 200

        data_type = mongo.data_types_collection.find_one({"sensor_id": util.objectid_to_str(sensors[0]["_id"]), "data_type": util.camel_to_snake(data_capture)})

        # Return empty data if no data_type found
        if not data_type:
            logger.warning(f"No data_type found for sensor_id: {util.objectid_to_str(sensors[0]['_id'])}, data_type: {util.camel_to_snake(data_capture)}")
            return jsonify({'data': []}), 200

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
        traceback.print_exc()
        return jsonify({'error': f'Failed to get metrics: {str(e)}'}), 500