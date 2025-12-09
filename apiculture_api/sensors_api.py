from datetime import datetime
from bson import ObjectId

from apiculture_api.app_util import AppUtil
util = AppUtil()

from flask import request, jsonify, Blueprint
sensors_api = Blueprint("sensors_api", __name__)

from apiculture_api.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('sensors_api')
logger.setLevel(logging.INFO)

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
        result = mongo.sensors_collection.insert_many(util.camel_to_snake_key(util.remove_id_key(data)))
        inserted_ids = util.objectid_to_str(result.inserted_ids)
        logger.info(f"Successfully saved sensors with IDs: {result.inserted_ids}")

        beehive_id = data[0]['beehiveId']
        if beehive_id:
            beehive = mongo.hives_collection.find_one({"_id": ObjectId(beehive_id)})
            for inserted_id in inserted_ids:
                beehive['sensor_ids'].append(inserted_id)
            beehive['updated_at'] = datetime.utcnow().isoformat(timespec='milliseconds')
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
        sensor['updated_at'] = datetime.utcnow().isoformat(timespec='milliseconds')
        sensor = util.camel_to_snake_key(util.remove_id_key(sensor))

        logger.info(f"sensor: {str(sensor)}")

        mongo.sensors_collection.update_one({"_id": ObjectId(id)}, {'$set': sensor}, upsert=False)

        logger.info(f"Successfully updated sensor with ID: {id}")
        return jsonify({'message': 'Sensor updated successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to update sensor: {str(e)}")
        return jsonify({'error': f'Failed to update sensor: {str(e)}'}), 500

@sensors_api.route('/api/sensors', methods=['GET'])
def get_sensors():
    try:
        sensors = util.snake_to_camel_key(util.objectid_to_str(list(mongo.sensors_collection.find())))
        logger.info(f'data: {sensors}')
        return jsonify({'data': sensors}), 200
    except Exception as e:
        logger.error(f"Failed to get sensors: {str(e)}")
        return jsonify({'error': f'Failed to get sensors: {str(e)}'}), 500