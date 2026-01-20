import random
import sys
import time
from datetime import datetime, timezone

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import DATA_COLLECTION_SIMULATION_FREQUENCY, DATA_COLLECTION_METRICS, API_HOST, API_PORT
from apiculture_api.util.task_runner import TaskRunner

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
    ],
    encoding='utf-8'
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
                if data_type["data_type"] != "honey_harvested":
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

            if has_anomaly:
                # Generate anomaly: value outside base_value +/- variance
                # Randomly choose to go above or below the normal range
                direction = 1 if random.random() > 0.5 else -1
                # Add extra deviation beyond the variance (1.5 to 3 times variance)
                anomaly_factor = random.uniform(1.5, 3.0)
                value = round((base_value + (direction * variance * anomaly_factor)) * 10) / 10
            else:
                # Normal reading: value within base_value +/- variance
                seed = (random.random() - 0.5) * 2 # Range: -1 to 1
                value = round((base_value + (seed * variance)) * 10) / 10
            data = [
                {
                    'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    'dataTypeId': util.objectid_to_str(data_type['_id']),
                    'value': value
                }
            ]
            if has_anomaly:
                logger.info(f"Sensor reading {str(data_type['data_type'])} with anomaly: {str(data)}")
            else:
                logger.info(f"Sensor reading {str(data_type['data_type'])} within the expected threshold: {str(data)}")
            response = requests.post(f'http://{API_HOST}:{API_PORT}/api/metrics', json=data)
            logger.info(response.json())

if __name__ == '__main__':
    DataCollectionSimulator().run()
