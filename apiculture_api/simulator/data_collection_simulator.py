import random
import time
from datetime import datetime, timezone

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import DATA_COLLECTION_SIMULATION_FREQUENCY
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

        base_value = None
        variance = None
        match data_type['data_type']:
            case 'temperature':
                base_value = 34.5
                variance = 2
            case 'humidity':
                base_value = 58
                variance = 5
            case 'co2':
                base_value = 420
                variance = 30
            case 'voc':
                base_value = 2.1
                variance = 0.3
            case 'sound':
                base_value = 68
                variance = 5
            case 'vibration':
                base_value = 0.3
                variance = 0.1
            case 'bee_count':
                base_value = 45000
                variance = 2000
            case 'lux':
                base_value = 1200
                variance = 200
            case 'uv_index':
                base_value = 4
                variance = 1
            case 'pheromone':
                base_value = 85
                variance = 10
            # case 'odor_compounds':
            #     base_value = 2.1
            #     variance = 0.3
            case 'rainfall':
                base_value = 0
                variance = 0.5
            case 'wind_speed':
                base_value = 5
                variance = 2
            case 'barometric_pressure':
                base_value = 1013
                variance = 5
            # case 'image':
            #     base_value = 2.1
            #     variance = 0.3
            case 'pollen_concentration':
                base_value = 65
                variance = 15
            # case 'activity':
            #     base_value = 2.1
            #     variance = 0.3

        if base_value is not None and variance is not None:
            value = round((base_value + (random.random() - 0.5) * variance) * 10) / 10
            data = [
                {
                    'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    'dataTypeId': util.objectid_to_str(data_type['_id']),
                    'value': value
                }
            ]
            print(data)
            response = requests.post('http://172.20.10.5:8080/api/metrics', json=data)
            print(response.json())

if __name__ == '__main__':
    DataCollectionSimulator().run()
