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

    def __init__(self, sensor_id=None, data_type_filter=None):
        """
        Initialize the data collection simulator

        Args:
             sensor_id: Optional sensor ID to simulate data for (None = all sensors)
             data_type_filter: Optional data type to simulate  (e.g., 'temperature', 'humidity')
        """
        self.sensor_id = sensor_id
        self.data_type_filter = data_type_filter

    def run_once(self):
        """Run data collection simulation once for all configured sensors."""
        if self.sensor_id:
            # Run for specific sensor
            try:
                sensor = mongo.sensors_collection.find_one({'_id': util.str_to_objectid(self.sensor_id)})
                if not sensor:
                    logger.error(f"Sensor not found: {self.sensor_id}")
                    return
                sensors = [sensor]
                logger.info(f"Running simulation for sensor: {sensor.get('name', self.sensor_id)}")
            except Exception as e:
                logger.error(f"Invalid sensor ID format: {self.sensor_id}, error: {e}")
                return
        else:
            # Run for all active sensors
            sensors = list(mongo.sensors_collection.find({'active': True}))
            logger.info(f'Running simulation for {len(sensors)} active sensor(s)')

        for sensor in sensors:
            data_types = list(mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id'])}))
            logger.info(f'Found: {len(data_types)} data_type(s) for sensor {sensor.get("name", sensor["_id"])}')

            for data_type in data_types:
                if data_type["data_type"] != "honey_harvested":
                    # Apply data type filter if specified
                    if self.data_type_filter and data_type["data_type"] != self.data_type_filter:
                        continue
                    self.generate_random_readings(data_type)

    def run(self, interval_seconds=None, max_runs=None):
        """
        Run data collection simulation continuously.

        Args:
             interval_seconds: Seconds between runs (default: DATA_COLLECTION_SIMULATION_FREQUENCY)
             max_runs: Maximum number of runs (None = infinite)
        """
        if interval_seconds is None:
            interval_seconds = DATA_COLLECTION_SIMULATION_FREQUENCY

        if self.sensor_id:
            # Run for specific sensor
            try:
                sensor = mongo.sensors_collection.find_one({'_id': util.str_to_objectid(self.sensor_id)})
                if not sensor:
                    logger.error(f"Sensor not found: {self.sensor_id}")
                    return
                sensors = [sensor]
                logger.info(f"Running continuous simulation for sensor: {sensor.get('name', self.sensor_id)}")
            except Exception as e:
                logger.error(f"Invalid sensor ID format: {self.sensor_id}, error: {e}")
                return
        else:
            # Run for all active sensors
            sensors = list(mongo.sensors_collection.find({'active': True}))
            logger.info(f'Running continuous simulation for {len(sensors)} active sensor(s)')

        tasks = []
        for sensor in sensors:
            data_types = list(mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id'])}))
            logger.info(f'data_types: {data_types}')

            for data_type in data_types:
                if data_type["data_type"] != "honey_harvested":
                    # Apply data type filter if specified
                    if self.data_type_filter and data_type["data_type"] != self.data_type_filter:
                        continue
                    tasks.append((self.generate_random_readings, (data_type,), interval_seconds))

        if not tasks:
            logger.error("No tasks to run. Check sensor configuration and filters.")
            return

        runner = TaskRunner(tasks)

        # If max_runs is specified, sleep for that duration, otherwise run for 24 hours
        if max_runs:
            sleep_time = interval_seconds * max_runs
            logger.info(f"Running for {max_runs} iterations ({sleep_time} seconds)")
        else:
            sleep_time = 60 * 60 * 24 # 24 hours
            logger.info(f"Running continuously for 24 hours")

        time.sleep(sleep_time)
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
    """
    Run teh data collection simulator.
    
    Usage:
        # Run once for all sensors
        python -m apiculture_api.simulator.data_collection_simulator
        
        # Run once for specific sensor
        python -m apiculture_api.simulator.data_collection_simulator --sensor-id 693b4c90943e75b9d619e11c
        
        # Run once for specific data type
        python -m apiculture_api.simulator.data_collection_simulator --data-type temperature
        
        # Run continuously with default interval
        python -m apiculture_api.simulator.data_collection_simulator --continuous
        
        # Run continuously with custom interval
        python -m apiculture_api.simulator.data_collection_simulator --continuous --interval 60
        
        # Run specific number of times
        python -m apiculture_api.simulator.data_collection_simulator --continuous --runs 10
        
        # Run for specific sensor and data type continuously
        python -m apiculture_api.simulator.data_collection_simulator --continuous --sensor-id 693b4c90943e75b9d619e11c --data-type humidity
        
        # Use hardcoded sensor (for IntelliJ quick testing)
        python -m apiculture_api.simulator.data_collection_simulator --use-hardcoded-sensor
    """
    import argparse

    parser = argparse.ArgumentParser(description='Data Collection Simulator - Simulates sensor data collection')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuously instead of once')
    parser.add_argument('--interval', type=int, default=None,
                        help=f'Seconds between simulations (default: {DATA_COLLECTION_SIMULATION_FREQUENCY})')
    parser.add_argument('--runs', type=int, default=None,
                        help=f'Maximum number of runs (default: infinite)')
    parser.add_argument('--sensor-id', type=str, default=None,
                        help='Specific sensor ID to simulate for')
    parser.add_argument('--data-type', type=str, default=None,
                        help='Specific data type to simulate (e.g., temperature, humidity)')
    parser.add_argument('--use-hardcoded-sensor', action='store_true',
                        hep='Use hardcoded sensor ID 693b4c90943e75b9d619e11c (for quick testing)')

    args = parser.parse_args()

    #Use hardcoded sensor if requested (useful for IntelliJ run configurations)
    sensor_id = args.sensor_id
    if args.use_hardcoded_sensor:
        sensor_id = '693b4c90943e75b9d619e11c'
        logger.info("Using hardcoded sensor ID: 693b4c90943e75b9d619e11c")

    simulator = DataCollectionSimulator(sensor_id=sensor_id, data_type_filter=args.data_type)

    if args.continuous:
        simulator.run(interval_seconds=args.interval, max_runs=args.runs)
    else:
        simulator.run_once()

