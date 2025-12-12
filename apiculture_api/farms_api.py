from datetime import datetime
from bson import ObjectId

from apiculture_api.app_util import AppUtil
util = AppUtil()

from flask import request, jsonify, Blueprint
farms_api = Blueprint("farms_api", __name__)

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
logger = logging.getLogger('farms_api')
logger.setLevel(logging.INFO)

@farms_api.route('/api/farms', methods=['POST'])
def save_farms():
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        result = mongo.farms_collection.insert_many(util.camel_to_snake_key(util.str_to_objectid(util.remove_id_key(data))))
        logger.info(f"Successfully saved farms with IDs: {result.inserted_ids}")
        return jsonify({'message': 'Data saved successfully', 'data': util.objectid_to_str(result.inserted_ids)}), 201
    except Exception as e:
        logger.error(f"Failed to save farms: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

@farms_api.route('/api/farms/<id>', methods=['PUT'])
def update_farm(id):
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        farm = mongo.farms_collection.find_one({"_id": ObjectId(id)})

        for key, value in data.items():
            farm[str(key)] = value
        farm['updated_at'] = datetime.utcnow().isoformat(timespec='milliseconds')
        farm = util.remove_id_key(farm)

        logger.info(f"farm: {str(farm)}")

        mongo.farms_collection.update_one({"_id": ObjectId(id)}, {'$set': util.camel_to_snake_key(farm)}, upsert=False)

        logger.info(f"Successfully updated farm with ID: {id}")
        return jsonify({'message': 'Farm updated successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to update farm: {str(e)}")
        return jsonify({'error': f'Failed to update farm: {str(e)}'}), 500

@farms_api.route('/api/farms', methods=['GET'])
def get_farms():
    try:
        farms = util.snake_to_camel_key(util.objectid_to_str(list(mongo.farms_collection.find())))
        logger.info(f'data: {farms}')
        return jsonify({'data': farms}), 200
    except Exception as e:
        logger.error(f"Failed to get farms: {str(e)}")
        return jsonify({'error': f'Failed to get farms: {str(e)}'}), 500

@farms_api.route('/api/farms/<id>', methods=['DELETE'])
def delete_farm(id):
    try:
        mongo.farms_collection.delete_one({"_id": ObjectId(id)})
        logger.info(f"Successfully deleted farm with ID: {id}")
        return jsonify({'message': 'Farm deleted successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to delete farm: {str(e)}")
        return jsonify({'error': f'Failed to delete farm: {str(e)}'}), 500
