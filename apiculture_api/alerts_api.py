from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from flask import jsonify, Blueprint
alerts_api = Blueprint("alerts_api", __name__)

from apiculture_api.util.mongo_client import ApicultureMongoClient
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
logger = logging.getLogger('alerts_api')
logger.setLevel(logging.INFO)

@alerts_api.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        alerts = util.snake_to_camel_key(util.objectid_to_str(list(mongo.alerts_collection.find())))
        logger.info(f'data: {alerts}')
        return jsonify({'data': alerts}), 200
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        return jsonify({'error': f'Failed to get alerts: {str(e)}'}), 500