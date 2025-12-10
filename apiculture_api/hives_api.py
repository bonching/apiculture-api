from datetime import datetime
from bson import ObjectId

from apiculture_api.app_util import AppUtil
util = AppUtil()

from flask import request, jsonify, Blueprint
hives_api = Blueprint("hives_api", __name__)

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
logger = logging.getLogger('hives_api')
logger.setLevel(logging.INFO)

@hives_api.route('/api/hives', methods=['POST'])
def save_hives():
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    logger.info(f"data: {data}")
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        result = mongo.hives_collection.insert_many(util.camel_to_snake_key(util.remove_id_key(data)))
        inserted_ids = util.objectid_to_str(result.inserted_ids)
        logger.info(f"Successfully saved hives with IDs: {result.inserted_ids}")

        farm_id = data[0]['farmId']
        farm = mongo.farms_collection.find_one({"_id": ObjectId(farm_id)})
        for inserted_id in inserted_ids:
            farm['beehive_ids'].append(inserted_id)
        farm['updated_at'] = datetime.utcnow().isoformat(timespec='milliseconds')
        farm = util.camel_to_snake_key(farm)
        mongo.farms_collection.update_one({"_id": ObjectId(farm_id)}, {'$set': farm}, upsert=False)

        return jsonify({'message': 'Data saved successfully', 'data': inserted_ids}), 201
    except Exception as e:
        logger.error(f"Failed to save hives: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

@hives_api.route('/api/hives/<id>', methods=['PUT'])
def update_hive(id):
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        hive = mongo.hives_collection.find_one({"_id": ObjectId(id)})

        for key, value in data.items():
            hive[str(key)] = value
        hive['updated_at'] = datetime.utcnow().isoformat(timespec='milliseconds')
        hive = util.camel_to_snake_key(util.remove_id_key(hive))

        logger.info(f"hive: {str(hive)}")

        mongo.hives_collection.update_one({"_id": ObjectId(id)}, {'$set': hive}, upsert=False)

        logger.info(f"Successfully updated hive with ID: {id}")
        return jsonify({'message': 'Hive updated successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to update hive: {str(e)}")
        return jsonify({'error': f'Failed to update hive: {str(e)}'}), 500

@hives_api.route('/api/hives', methods=['GET'])
def get_hives():
    try:
        hives = util.snake_to_camel_key(util.objectid_to_str(list(mongo.hives_collection.find())))
        logger.info(f'data: {hives}')
        return jsonify({'data': hives}), 200
    except Exception as e:
        logger.error(f"Failed to get hives: {str(e)}")
        return jsonify({'error': f'Failed to get hives: {str(e)}'}), 500

@hives_api.route('/api/hives/<id>', methods=['DELETE'])
def delete_hive(id):
    try:
        mongo.hives_collection.delete_one({"_id": ObjectId(id)})
        logger.info(f"Successfully deleted hive with ID: {id}")
        return jsonify({'message': 'Hive deleted successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to delete hive: {str(e)}")
        return jsonify({'error': f'Failed to delete hive: {str(e)}'}), 500
