import random
import time
from datetime import datetime, timezone

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import DATA_COLLECTION_SIMULATION_FREQUENCY, DATA_COLLECTION_METRICS, API_HOST, API_PORT
from apiculture_api.util.task_runner import TaskRunner

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
logger = logging.getLogger('data_collection_simulator')
logger.setLevel(logging.INFO)

class DataCollectionSimulator:

    def __init__(self):
        pass

    def run(self):
        sensors = list(mongo.sensors_collection.find({ 'active': True}))
        logger.info(f'sensors: {sensors}')

        tasks = []
        for sensor in sensors:
            data_types = list(mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id'])}))
            logger.info(f'data_types: {data_types}')

            for data_type in data_types:
                tasks.append((self.generate_random_readings, (data_type,), DATA_COLLECTION_SIMULATION_FREQUENCY))

        runner = TaskRunner(tasks)
        time.sleep(60*60*24)
        runner.shutdown(wait=True)

    def generate_random_readings(self, data_type):
        sensor = mongo.sensors_collection.find_one({'_id': util.str_to_objectid(data_type['sensor_id'])})
        if sensor is None or sensor['active'] is False or sensor['simulate'] is False:
            logger.info(f"Skipping simulation of sensor: {sensor['name']}")
            return

        logger.info(f"generating random readings for data type: {str(data_type)}")

        base_value = DATA_COLLECTION_METRICS[data_type['data_type']]['base_value']
        variance = DATA_COLLECTION_METRICS[data_type['data_type']]['variance']

        if base_value is not None and variance is not None:
            anomaly_rate = random.uniform(0.01, 100.00)
            has_anomaly = anomaly_rate < DATA_COLLECTION_METRICS[data_type['data_type']]['anomaly_rate']

            seed = (random.random() - 0.5)
            value = round((base_value + (seed * variance) + (2 * variance if has_anomaly else 0)) * 10) / 10
            data = [
                {
                    'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    'dataTypeId': util.objectid_to_str(data_type['_id']),
                    'value': value
                }
            ]
            if has_anomaly:
                logger.info(f"Sensor reading within the expected threshold: {str(data_type)}")
            else:
                logger.info(f"Sensor reading with anomaly: {str(data_type)}")
            response = requests.post(f'http://{API_HOST}:{API_PORT}/api/metrics', json=data)
            logger.info(response.json())

if __name__ == '__main__':
    DataCollectionSimulator().run()
