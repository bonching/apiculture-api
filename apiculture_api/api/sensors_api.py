import traceback
from datetime import datetime, timezone
from bson import ObjectId

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from flask import request, jsonify, Blueprint
sensors_api = Blueprint("sensors_api", __name__)

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
logger = logging.getLogger('sensors_api')
logger.setLevel(logging.INFO)

data_type_units = {
    'temperature': '°C',
    'humidity': '%',
    'co2': 'ppm',
    'voc': 'kΩ',
    'sound': 'dB',
    'vibration': 'mm/s',
    'bee_count': '',
    'lux': 'lux',
    'uv_index': '',
    'pheromone': '',
    'odor_compounds': '',
    'rainfall': 'mm',
    'wind_speed': 'km/h',
    'barometric_pressure': 'hPa',
    'image': '',
    'pollen_concentration': '',
    'activity': ''
}

@sensors_api.route('/api/sensors', methods=['POST'])
def save_sensors():
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    logger.info(f"data: {data}")
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        for record in data:
            record['created_at'] = datetime.now(timezone.utc)
        result = mongo.sensors_collection.insert_many(util.camel_to_snake_key(util.str_to_objectid(util.remove_id_key(data))))
        inserted_ids = util.objectid_to_str(result.inserted_ids)
        logger.info(f"Successfully saved sensors with IDs: {result.inserted_ids}")

        beehive_id = data[0]['beehiveId']
        if beehive_id:
            beehive = mongo.hives_collection.find_one({"_id": ObjectId(beehive_id)})
            for inserted_id in inserted_ids:
                beehive['sensor_ids'].append(inserted_id)

                sensor = mongo.sensors_collection.find_one({"_id": ObjectId(inserted_id)})
                logger.info(f"sensor: {sensor}")
                for data_type in sensor['data_capture']:
                    result = mongo.data_types_collection.insert_one({
                        "sensor_id": inserted_id,
                        "data_type": data_type,
                        "unit": data_type_units[data_type],
                        "updated_at": datetime.now(timezone.utc)
                    })
                    logger.info(f"Successfully saved data type {data_type} with ID: {result.inserted_id}")

            beehive['updated_at'] = datetime.now(timezone.utc)
            beehive = util.camel_to_snake_key(beehive)
            mongo.hives_collection.update_one({"_id": ObjectId(beehive_id)}, {'$set': beehive}, upsert=False)

        return jsonify({'message': 'Data saved successfully', 'data': inserted_ids}), 201
    except Exception as e:
        logger.error(f"Failed to save sensors: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

@sensors_api.route('/api/sensors/<id>', methods=['PUT'])
def update_sensor(id):
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        sensor = mongo.sensors_collection.find_one({"_id": ObjectId(id)})

        for key, value in data.items():
            sensor[str(key)] = value
        sensor['updated_at'] = datetime.now(timezone.utc)
        sensor = util.camel_to_snake_key(util.remove_id_key(sensor))

        logger.info(f"sensor: {str(sensor)}")

        mongo.sensors_collection.update_one({"_id": ObjectId(id)}, {'$set': sensor}, upsert=False)

        for data_type in data['dataCapture']:
            sensor_data_type = mongo.data_types_collection.find_one({"sensor_id": id, "data_type": data_type})
            if sensor_data_type is None:
                unit = data_type_units[data_type]
                result = mongo.data_types_collection.insert_one({
                    'sensor_id': id,
                    'data_type': data_type,
                    'unit': unit
                })
                logger.info(f"Successfully saved data type {data_type} with ID: {result.inserted_id}")

        logger.info(f"Successfully updated sensor with ID: {id}")
        return jsonify({'message': 'Sensor updated successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to update sensor: {str(e)}")
        return jsonify({'error': f'Failed to update sensor: {str(e)}'}), 500

@sensors_api.route('/api/sensors', methods=['GET'])
def get_sensors():
    try:
        sensors = list(mongo.sensors_collection.find({"active": True}))

        for sensor in sensors:
            latest_readings = []
            last_updated = None
            for data_capture in sensor['data_capture']:
                data_type = mongo.data_types_collection.find_one({"sensor_id": util.objectid_to_str(sensor["_id"]), "data_type": data_capture})
                # logger.info(f"data_type: {data_type}")
                if data_type is None:
                    continue

                data_type_id = util.objectid_to_str(data_type["_id"])
                unit = data_type['unit']
                metrics = mongo.metrics_collection.find({"data_type_id": data_type_id}).sort("datetime", -1).limit(1)
                for metric in metrics:
                    latest_readings.append(f"{metric['value']}{unit}")
                    last_updated = metric['datetime'] if last_updated is None or last_updated < metric['datetime'] else last_updated
                    logger.info(f"last_updated: {last_updated}")
                    break

            if len(latest_readings) > 0:
                sensor['currentValue'] = ', '.join(latest_readings)
                sensor['lastUpdated'] = util.time_ago(int(last_updated.replace(tzinfo=timezone.utc).timestamp()))

        sensors = util.snake_to_camel_key(util.objectid_to_str(sensors))
        logger.info(f'data: {sensors}')
        return jsonify({'data': sensors}), 200
    except Exception as e:
        logger.error(f"Failed to get sensors: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to get sensors: {str(e)}'}), 500

@sensors_api.route('/api/sensors/<id>', methods=['DELETE'])
def delete_sensor(id):
    try:
        mongo.sensors_collection.delete_one({"_id": ObjectId(id)})
        logger.info(f"Successfully deleted sensor with ID: {id}")
        return jsonify({'message': 'Sensor deleted successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to delete sensor: {str(e)}")
        return jsonify({'error': f'Failed to delete sensor: {str(e)}'}), 500
