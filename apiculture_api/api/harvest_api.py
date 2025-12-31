import traceback
import threading
import time
from datetime import datetime, timezone
from bson import ObjectId

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from apiculture_api.util.iot_client import IoTClient

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


def simulate_harvest(harvest_id):
    """
    Background Task to simulate harvest progression through states:
    calibrating the device -> starting smoker -> capturing beehive interior images
    -> analyzing honeypots -> harvesting honey -> completed
    """
    logger.info(f"Starting harvest simulation for {harvest_id}")

    # State 1: Calibrating the device (0-15%)
    with harvest_jobs_lock:
        harvest_jobs[harvest_id] = {
            'state': 'calibrating',
            'progress': 0,
            'started_at': datetime.now(timezone.utc).isoformat()
        }

    # Connect to IoT Websocket and send servo motor command
    logger.info(f"[{harvest_id}] Connecting to IoT Websocket...")
    try:
        with IoTClient() as iot_client:
            # Send servo motor command
            response = iot_client.send_command({'angle': 90})

            if response.get('success', False):
                logger.info(f"[{harvest_id}] Servo motor command sent successfully")
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['servo_status'] = 'success'
            else:
                logger.error(f"[{harvest_id}] Failed to send servo motor command: {response.get('error', 'Unknown error')}")
                with harvest_jobs_lock:
                    if harvest_id in harvest_jobs:
                        harvest_jobs[harvest_id]['servo_status'] = 'failed'
                        harvest_jobs[harvest_id]['servo_error'] = response.get('error', 'Unknown error')
    except Exception as e:
        logger.error(f"[{harvest_id}] Failed to connect to IoT Websocket: {str(e)}")
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['servo_status'] = 'failed'
                harvest_jobs[harvest_id]['servo_error'] = str(e)

    for i in range(0, 16, 5):
        time.sleep(1) # Simulate time passing
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['progress'] = i

    # State 2: Starting smoker (15-30%)
    with harvest_jobs_lock:
        if harvest_id in harvest_jobs:
            harvest_jobs[harvest_id]['state'] = 'starting_smoker'

    for i in range(15, 31, 5):
        time.sleep(1)
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['progress'] = i

    # State 3: Capturing beehive interior images (30-50%)
    with harvest_jobs_lock:
        if harvest_id in harvest_jobs:
            harvest_jobs[harvest_id]['state'] = 'capturing_images'

    for i in range(30, 51, 5):
        time.sleep(1)
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['progress'] = i

    # State 4: Analyzing honeypots (50-70%)
    with harvest_jobs_lock:
        if harvest_id in harvest_jobs:
            harvest_jobs[harvest_id]['state'] = 'analyzing_honeypots'

    for i in range(50, 71, 5):
        time.sleep(1)
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['progress'] = i

    # State 5: Harvesting honey (70-100%)
    with harvest_jobs_lock:
        if harvest_id in harvest_jobs:
            harvest_jobs[harvest_id]['state'] = 'harvesting'

    for i in range(70, 101, 5):
        time.sleep(1)
        with harvest_jobs_lock:
            if harvest_id in harvest_jobs:
                harvest_jobs[harvest_id]['progress'] = i

    # State 6: Completed
    with harvest_jobs_lock:
        if harvest_id in harvest_jobs:
            harvest_jobs[harvest_id]['state'] = 'completed'
            harvest_jobs[harvest_id]['progress'] = 100
            harvest_jobs[harvest_id]['completed_at'] = datetime.now(timezone.utc).isoformat()

    logger.info(f"Harvest simulation completed for {harvest_id}")


@harvest_api.route('/api/harvest', methods=['POST'])
def start_harvest():
    """
    Start a new harvest job
    Returns a unique harvest_id

    The harvest progress through these states:
    1. calibrating the device (0-15%)
    2. starting smoker (15-30%)
    3. capturing beehive interior images (30-50%)
    4. analyzing honeypots (50-70%)
    5. harvesting honey (70-100%)
    6. completed (100%)
    """
    try:
        # Generate a unique harvest_id
        harvest_id = str(ObjectId())

        logger.info(f"Starting new harvest with ID: {harvest_id}")

        # Initialize harest job
        with harvest_jobs_lock:
            harvest_jobs[harvest_id] = {
                'state': 'calibrating the device',
                'progress': 0,
                'started_at': datetime.now(timezone.utc).isoformat()
            }

        # Start background simulation thread
        thread = threading.Thread(target=simulate_harvest, args=(harvest_id,), daemon=True)
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