import random
from datetime import datetime, timezone

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import DATA_COLLECTION_METRICS, API_HOST, API_PORT

util = AppUtil()

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
logger = logging.getLogger('harvest_simulator')
logger.setLevel(logging.INFO)

class HarvestSimulator:

    def __init__(self):
        pass

    def run(self):
        sensors = list(mongo.sensors_collection.find({ 'active': True, 'simulate': True, 'data_capture': 'honey_harvested'}))
        logger.info(f'found: {len(sensors)} sensors')

        for sensor in sensors:
            logger.info(f"sensor: {sensor}")

            data_types = list(mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id'])}))
            logger.info(f'found: {len(data_types)} data_types')

            for data_type in data_types:
                base_value = DATA_COLLECTION_METRICS[data_type['data_type']]['base_value']
                variance = DATA_COLLECTION_METRICS[data_type['data_type']]['variance']

                seed = (random.random() - 0.5)
                value = round(base_value + (seed * variance) * 10) / 10
                data = [
                    {
                        'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                        'dataTypeId': util.objectid_to_str(data_type['_id']),
                        'value': value
                    }
                ]
                logger.info(f'Honey harvested: {str(data)}')
                response = requests.post(f'http://{API_HOST}:{API_PORT}/api/metrics', json=data)
                logger.info(response.json())

if __name__ == '__main__':
    HarvestSimulator().run()
