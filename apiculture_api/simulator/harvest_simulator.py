import random
import sys
from datetime import datetime, timezone

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import DATA_COLLECTION_METRICS, API_HOST, API_PORT

util = AppUtil()

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
        logging.FileHandler('apiculture-api.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('harvest_simulator')
logger.setLevel(logging.INFO)

class HarvestSimulator:

    def __init__(self):
        pass

    def run(self):
        sensor_id = '693b4c90943e75b9d619e139' # this sensor is not attached to any beehive (harvest sensor)
        beehive_id = '693ad7c84739d5289a1e0835'

        # Query the data_types collection to get the honey_harvested data type ID
        data_type = mongo.data_types_collection.find_one({
            'sensor_id': sensor_id,
            'data_type': 'honey_harvested'
        })

        if not data_type:
            logger.info(f"Could not find honey_harvested data type for sensor {sensor_id}")
            return

        data_type_id = util.objectid_to_str(data_type['_id'])
        logger.info(f"Found honey_harvested data type ID: {data_type_id}")

        base_value = DATA_COLLECTION_METRICS['honey_harvested']['base_value']
        variance = DATA_COLLECTION_METRICS['honey_harvested']['variance']

        value = round(base_value + (random.random() * variance) * 10) / 10
        data = [
            {
                'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                'dataTypeId': data_type_id,
                'beehiveId': beehive_id,
                'value': value
            }
        ]
        logger.info(f'Honey harvested: {str(data)}')
        response = requests.post(f'http://{API_HOST}:{API_PORT}/api/metrics', json=data)
        logger.info(response.json())

if __name__ == '__main__':
    HarvestSimulator().run()
