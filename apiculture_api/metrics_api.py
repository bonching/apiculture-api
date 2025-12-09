from apiculture_api.app_util import AppUtil
util = AppUtil()

from flask import request, jsonify, Blueprint
metrics_api = Blueprint("metrics_api", __name__)

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
        result = mongo.metrics_collection.insert_many(util.fix_datetime(util.remove_id_key(data)))
        inserted_ids = util.objectid_to_str(result.inserted_ids)
        logger.info(f"Successfully saved metrics with IDs: {result.inserted_ids}")

        return jsonify({'message': 'Data saved successfully', 'data': inserted_ids}), 201
    except Exception as e:
        logger.error(f"Failed to save metrics: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

@metrics_api.route('/api/metrics', methods=['GET'])
def get_metrics():
    try:
        metrics = list(mongo.metrics_collection.find())
        logger.info(f'data: {util.objectid_to_str(metrics)}')
        return jsonify({'data': util.objectid_to_str(metrics)}), 200
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        return jsonify({'error': f'Failed to get metrics: {str(e)}'}), 500