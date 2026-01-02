import random
import traceback
import threading
import time
from datetime import datetime, timezone
from bson import ObjectId

from apiculture_api.api.metrics_api import save_metrics
from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from apiculture_api.util.iot_client import IoTClient
from apiculture_api.util.config import IOT_SIMULATE_MODE, DATA_COLLECTION_METRICS, HARVEST_DEVICE

from flask import request, jsonify, Blueprint
harvest_api = Blueprint("harvest_api", __name__)

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('../apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('harvest_api')
logger.setLevel(logging.INFO)

# In-memory store for harvest progress (for simplicity)
# In production, this should be stored in a database
harvest_jobs = {}
harvest_jobs_lock = threading.Lock()


def initiate_harvest(harvest_id):
    """
    Event driven harvest state machine.
    Each state emits event and registers a callback for the next state.

    States:
    1. calibrating -> starting_smoker
    2. starting_smoker -> capturing_images
    3. capturing_images -> analyzing_honeypots
    4. analyzing_honeypots -> harvesting
    5. harvesting -> completed
    """
    logger.info(f"Starting event-driven harvest for {harvest_id}")

    # Create Iot client instance for this harvest
    iot_client = IoTClient()

    try:
        # Connect to IoT device
        if not iot_client.connect():
            logger.error(f"Failed to connect to IoT client")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['state'] = 'failed'
                    harvest_jobs[harvest_id]['progress'] = 0
                    harvest_jobs[harvest_id]['error'] = 'Failed to connect to IoT client'
                    harvest_jobs[harvest_id]['failed_at'] = datetime.now(timezone.utc).isoformat()
            return

        # Define state transition callbacks
        def on_calibrating_complete(data):
            """Callback for calibrating -> starting_smoker"""
            logger.info(f"calibrating completed for {harvest_id}, response: {data}")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['calibrating_response'] = data

            # Transition to next state
            execute_starting_smoker()

        def on_starting_smoker_complete(data):
            """Callback for starting_smoker -> capturing_images"""
            logger.info(f"starting_smoker completed for {harvest_id}, response: {data}")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['starting_smoker_response'] = data

            execute_capturing_images()

        def on_capturing_images_complete(data):
            """Callback for capturing_images -> analyzing_honeypots"""
            logger.info(f"capturing_images completed for {harvest_id}, response: {data}")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['capturing_images_response'] = data

            execute_analyzing_honeypots()

        def on_analyzing_honeypots_complete(data):
            """Callback for analyzing_honeypots -> harvesting"""
            logger.info(f"analyzing_honeypots completed for {harvest_id}, response: {data}")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['analyzing_honeypots_response'] = data

            execute_harvesting()

        def on_harvesting_complete(data):
            """Callback for harvesting -> completed"""
            logger.info(f"harvesting completed for {harvest_id}, response: {data}")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['harvesting_response'] = data

            execute_completed()

        # State execution functions
        def execute_calibrating():
            """State 1: calibrating (0-5%)"""
            logger.info(f"{harvest_id} Executing state: calibrating")
            with harvest_jobs_lock:
                harvest_jobs[harvest_id] = {
                    'state': 'calibrating',
                    'progress': 0,
                    'start_at': datetime.now(timezone.utc).isoformat()
                }

            # Update progress (with delays only on simulation mode)
            if IOT_SIMULATE_MODE:
                # Explicit delays for simulation mode
                for i in range(0, 6, 1):
                    time.sleep(1)
                    with harvest_jobs_lock:
                        if harvest_id in harvest_jobs and harvest_jobs[harvest_id]['state'] == 'calibrating':
                            harvest_jobs[harvest_id]['progress'] = i
            else:
                # No explicit delays for real IoT device - rely on device response time
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['progress'] = 5

            # Register callback for next state AFTER progress completes
            iot_client.register_response_callback('needle_servo:response', on_calibrating_complete)

            # Emit event to IoT device (callback will trigger next state)
            response = iot_client.emit_event('needle_servo:angle', {'angle': 90, 'state': 'calibrating'})
            logger.info(f"Emitted event with response: {response}")

        def execute_starting_smoker():
            """State 2: starting_smoker (6-20%)"""
            logger.info(f"{harvest_id} Executing state: starting_smoker")
            with harvest_jobs_lock:
                harvest_jobs[harvest_id] = {
                    'state': 'starting_smoker'
                }

            if IOT_SIMULATE_MODE:
                for i in range(6, 21, 1):
                    time.sleep(1)
                    with harvest_jobs_lock:
                        if harvest_id in harvest_jobs and harvest_jobs[harvest_id]['state'] == 'starting_smoker':
                            harvest_jobs[harvest_id]['progress'] = i
            else:
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['progress'] = 20

            iot_client.unregister_response_callback('needle_servo:response')
            iot_client.register_response_callback('needle_servo:response', on_starting_smoker_complete)

            response = iot_client.emit_event('needle_servo:angle', {'angle': 45, 'state': 'starting_smoker'})
            logger.info(f"Emitted event with response: {response}")

        def execute_capturing_images():
            """State 3: capturing_images (21-30%)"""
            logger.info(f"{harvest_id} Executing state: capturing_images")
            with harvest_jobs_lock:
                harvest_jobs[harvest_id] = {
                    'state': 'capturing_images'
                }

            if IOT_SIMULATE_MODE:
                for i in range(21, 31, 1):
                    time.sleep(1)
                    with harvest_jobs_lock:
                        if harvest_id in harvest_jobs and harvest_jobs[harvest_id]['state'] == 'capturing_images':
                            harvest_jobs[harvest_id]['progress'] = i
            else:
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['progress'] = 30

            iot_client.unregister_response_callback('needle_servo:response')
            iot_client.register_response_callback('needle_servo:response', on_capturing_images_complete)

            response = iot_client.emit_event('needle_servo:angle', {'angle': 75, 'state': 'capturing_images'})
            logger.info(f"Emitted event with response: {response}")

        def execute_analyzing_honeypots():
            """State 4: analyzing_honeypots (31-32%)"""
            logger.info(f"{harvest_id} Executing state: analyzing_honeypots")
            with harvest_jobs_lock:
                harvest_jobs[harvest_id] = {
                    'state': 'analyzing_honeypots'
                }

            if IOT_SIMULATE_MODE:
                for i in range(31, 33, 1):
                    time.sleep(1)
                    with harvest_jobs_lock:
                        if harvest_id in harvest_jobs and harvest_jobs[harvest_id]['state'] == 'analyzing_honeypots':
                            harvest_jobs[harvest_id]['progress'] = i
            else:
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['progress'] = 32

            iot_client.unregister_response_callback('needle_servo:response')
            iot_client.register_response_callback('needle_servo:response', on_analyzing_honeypots_complete)

            response = iot_client.emit_event('needle_servo:angle', {'angle': 15, 'state': 'analyzing_honeypots'})
            logger.info(f"Emitted event with response: {response}")

        def execute_harvesting():
            """State 5: harvesting (33-100%)"""
            logger.info(f"{harvest_id} Executing state: harvesting")
            with harvest_jobs_lock:
                harvest_jobs[harvest_id] = {
                    'state': 'harvesting'
                }

            if IOT_SIMULATE_MODE:
                for i in range(33, 101, 1):
                    time.sleep(1)
                    with harvest_jobs_lock:
                        if harvest_id in harvest_jobs and harvest_jobs[harvest_id]['state'] == 'harvesting':
                            harvest_jobs[harvest_id]['progress'] = i
            else:
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['progress'] = 100

            iot_client.unregister_response_callback('needle_servo:response')
            iot_client.register_response_callback('needle_servo:response', on_harvesting_complete)

            response = iot_client.emit_event('needle_servo:angle', {'angle': 180, 'state': 'harvesting'})
            logger.info(f"Emitted event with response: {response}")

        def execute_completed():
            """State 6: completed (100%)"""
            logger.info(f"{harvest_id} Executing state: completed")
            with harvest_jobs_lock:
                if harvest_id in harvest_jobs:
                    harvest_jobs[harvest_id]['state'] = 'completed'
                    harvest_jobs[harvest_id]['progress'] = 100
                    harvest_jobs[harvest_id]['completed_at'] = datetime.now(timezone.utc).isoformat()

            if IOT_SIMULATE_MODE:
                logger.info(f"{harvest_id} simulation completed")

            # Cleanup
            iot_client.unregister_response_callback('needle_servo:response')
            iot_client.close()

            # Save the harvested metrics
            base_value = DATA_COLLECTION_METRICS['honey_harvested']['base_value']
            variance = DATA_COLLECTION_METRICS['honey_harvested']['variance']
            value = round(base_value + (random.random() * variance) * 10) / 10
            data = [
                {
                    'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    'dataTypeId': HARVEST_DEVICE['data_type_id'],
                    'beehiveId': harvest_jobs[harvest_id].get('beehive_id'),
                    'value': value
                }
            ]
            logger.info(f'Honey harvested: {str(data)}')
            response = save_metrics(data)
            logger.info(response.json())

        # Start the state machine with the first state
        execute_calibrating()

    except Exception as e:
        logger.error(f"[{harvest_id}] Error in harvest state machine: {str(e)}")
        traceback.print_exc()
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['servo_status'] = 'failed'
                harvest_jobs[harvest_id]['servo_error'] = str(e)
                harvest_jobs[harvest_id]['failed_at'] = datetime.now(timezone.utc).isoformat()

        # Cleanup on error
        try:
            iot_client.close()
        except:
            pass

@harvest_api.route('/api/harvest', methods=['POST'])
def start_harvest():
    """
    Start a new harvest job
    Returns a unique harvest_id

    The harvest progress through these states:
    1. calibrating the device (0-5%)
    2. starting smoker (6-20%)
    3. capturing beehive interior images (21-30%)
    4. analyzing honeypots (31-32%)
    5. harvesting honey (33-100%)
    6. completed (100%)
    """
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    device_id = data['deviceId']
    beehive_id = data['beehiveId']

    try:
        # Generate a unique harvest_id
        harvest_id = str(ObjectId())

        logger.info(f"Starting new harvest with ID: {harvest_id}")

        # Initialize harvest job
        with harvest_jobs_lock:
            harvest_jobs[harvest_id] = {
                'device_id': device_id,
                'beehive_id': beehive_id,
                'state': 'calibrating',
                'progress': 0,
                'started_at': datetime.now(timezone.utc).isoformat()
            }

        # Start background simulation thread
        thread = threading.Thread(target=initiate_harvest, args=(harvest_id,), daemon=True)
        thread.start()

        return jsonify({
            'harvest_id': harvest_id,
            'message': 'Harvest started successfully'
        }), 201
    except Exception as e:
        logger.error(f"Failed to start harvest: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to start harvest: {str(e)}'}), 500


@harvest_api.route('/api/harvest/<harvest_id>', methods=['GET'])
def get_harvest_progress(harvest_id):
    """
    Get the progress of a specific harvest job
    Returns the current state and progress
    """
    try:
        with harvest_jobs_lock:
            if harvest_id not in harvest_jobs:
                return jsonify({'error': 'Harvest job not found'}), 404

            job = harvest_jobs[harvest_id]

        return jsonify({
            'state': job['state'],
            'progress': job['progress']
        }), 200
    except Exception as e:
        logger.error(f"Failed to get harvest progress: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to get harvest progress: {str(e)}'}), 500