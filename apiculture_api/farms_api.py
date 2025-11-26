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
        result = mongo.farms_collection.insert_many(data)
        logger.info(f"Successfully saved farms with ID: {result.inserted_ids}")
        return jsonify({'message': 'Data saved successfully', 'inserted_id': str(result.inserted_ids)}), 201
    except Exception as e:
        logger.error(f"Failed to save farms: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500
