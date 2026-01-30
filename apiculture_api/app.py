import sys
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone

from apiculture_api.api.farms_api import farms_api
from apiculture_api.api.hives_api import hives_api
from apiculture_api.api.sensors_api import sensors_api
from apiculture_api.api.metrics_api import metrics_api
from apiculture_api.api.harvest_api import harvest_api
from apiculture_api.alerts_api import alerts_api, enqueue_sse

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import SENSOR_HEARTBEAT_FREQUENCY, IDLE_TIME_TO_MARK_SENSOR_AS_OFFLINE, API_PORT
from apiculture_api.util.task_runner import TaskRunner

util = AppUtil()

# ML / AI
from apiculture_api.ai.predator_detector import analyze_predators
from apiculture_api.ai.bee_counter import count_bees

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
logger = logging.getLogger('app')
logger.setLevel(logging.INFO)

# Create the Flask application
app = Flask(__name__)
app.register_blueprint(farms_api)
app.register_blueprint(hives_api)
app.register_blueprint(sensors_api)
app.register_blueprint(metrics_api)
app.register_blueprint(harvest_api)
app.register_blueprint(alerts_api)

CORS(
    app,
    origins=['*'],
)

# Set up MongoDB connection
from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()


@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    Endpoint to receive IoT sensor data via POST request.
    Expects JSON body with sensor readings, e.g., {"temperature": 25.5, "humidity": 60}.
    Parses the JSON into a Python dict and inserts it into MongoDB.
    """
    logger.info(f"Received POST request to /api/sensor-data from {request.remote_addr}")

    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        # Insert the data into MongoDB
        result = mongo.sensor_collection.insert_one(data)
        logger.info(f"Successfully saved sensor data with ID: {result.inserted_id}")
        return jsonify({'message': 'Data saved successfully', 'inserted_id': str(result.inserted_id)}), 201
    except Exception as e:
        logger.error(f"Failed to save sensor data: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500


@app.route('/api/images', methods=['POST'])
def upload_image():
    """
    Endpoint to receive an image file via POST request.
    Expects a multipart/form-data request with an 'image' file.
    Stores the image as binary data in the MongoDB 'images' collection and saves to local disk.
    """
    logger.info(f"Received POST request to /api/upload-image from {request.remote_addr}")

    if 'image' not in request.files:
        logger.warning("No image file provided in request")
        return jsonify({'error': 'No image file provided'}), 400

    image_file = request.files['image']
    if not image_file or image_file.filename == '':
        logger.warning("Empty or invalid image file")
        return jsonify({'error': 'Invalid image file'}), 400

    # Validate file type (allow common image formats)
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if not '.' in image_file.filename or image_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        logger.warning(f"Unsupported file type for {image_file.filename}")
        return jsonify({'error': 'Unsupported file type. Allowed: png, jpg, jpeg, gif'}), 400

    context = request.form.get('context')
    sensor_id = request.form.get('sensorId')

    try:
        import os
        import requests

        # Create images directory if it doesn't exist
        images_dir = 'uploaded_images'
        os.makedirs(images_dir, exist_ok=True)

        # Save to local disk
        filepath = os.path.join(images_dir, image_file.filename)
        image_file.save(filepath)
        logger.info(f"Successfully saved image {image_file.filename} to {filepath}")

        # Read image as binary for MongoDB
        image_file.seek(0) # Reset file pointer after saving
        image_data = image_file.read()

        # Run predator analysis only for defense context (before inserting, so we can store result too)
        predator_result = None
        if context == 'defense':
            predator_result = analyze_predators(image_data, content_type=image_file.content_type)
            logger.info(
                "Predator analysis result: detected=%s confidence=%s predator=%s",
                predator_result.predator_detected,
                predator_result.confidence,
                predator_result.predator
            )

        # Run bee counting only for data collection context.
        bee_count_result = None
        if context == 'data_collection':
            bee_count_result = count_bees(image_data, content_type=image_file.content_type)
            logger.info(
                "Bee count result: count=%s confidence=%s",
                bee_count_result.bee_count,
                bee_count_result.confidence
            )
            # Note: Metric saving is handled by the caller (e.g., data_collection_simulator)
            # to avoid duplicate saves and allow proper anomaly detection flow

        # Run honeypot analysis for harvest context
        honeypot_result = None
        if context == 'harvest':
            from apiculture_api.ai.honeypots_analyzer import analyze_honeypots
            honeypot_result = analyze_honeypots(image_data, content_type=image_file.content_type)
            logger.info(
                "Honeypot analysis result: detected=%s total=%s filled=%s fill_percentage=%s%% confidence=%s",
                honeypot_result.honeypots_detected,
                honeypot_result.total_honeypots,
                honeypot_result.filled_honeypots,
                honeypot_result.fill_percentage,
                honeypot_result.confidence
            )

        # Create document with image data and metadata
        image_doc = {
            'filename': image_file.filename,
            'data': image_data,
            'sensor_id': sensor_id,
            'content_type': image_file.content_type,
            'upload_time': datetime.now(timezone.utc)
        }
        if context is not None:
            image_doc['context'] = context
        if predator_result is not None:
            image_doc['predator_analysis'] = {
                'predator_detected': bool(predator_result.predator_detected),
                'confidence': float(predator_result.confidence),
                'predator': predator_result.predator,
                'details': predator_result.details,
                'analyzed_at': datetime.now(timezone.utc)
            }
        if bee_count_result is not None:
            image_doc['bee_count'] = {
                'count': int(bee_count_result.bee_count),
                'confidence': float(bee_count_result.confidence),
                'details': bee_count_result.details,
                'analyzed_at': datetime.now(timezone.utc)
            }
        if honeypot_result is not None:
            image_doc['honeypot_analysis'] = {
                'honeypots_detected': bool(honeypot_result.honeypots_detected),
                'total_honeypots': int(honeypot_result.total_honeypots),
                'filled_honeypots': int(honeypot_result.filled_honeypots),
                'empty_honeypots': int(honeypot_result.empty_honeypots),
                'fill_percentage': float(honeypot_result.fill_percentage),
                'confidence': float(honeypot_result.confidence),
                'grid_analysis': honeypot_result.grid_analysis,
                'honeypot_locations': honeypot_result.honeypot_locations,
                'details': honeypot_result.details,
                'analyzed_at': datetime.now(timezone.utc)
            }

        # Insert into MongoDB
        result = mongo.image_collection.insert_one(image_doc)
        logger.info(f"Successfully saved image {image_file.filename} with ID: {result.inserted_id}")
        response = {
            'message': 'Image uploaded successfully',
            'imageId': str(result.inserted_id),
            'filename': image_file.filename
        }

        if predator_result is not None:
            response['predator_analysis'] = image_doc['predator_analysis']
            response['imageId'] = str(result.inserted_id)

            # Only run sprinkler when a predator is actually detected.
            if predator_result.predator_detected:
                response['run_sprinkler'] = 'Y'

                # Notify the beekeeper
                try:
                    # Get sensor, hive, and farm information for context
                    sensor = None
                    hive = None
                    farm = None

                    if sensor_id:
                        sensor = mongo.sensors_collection.find_one({"_id": util.str_to_objectid(sensor_id)})
                        if sensor and sensor.get('beehive_id'):
                            hive = mongo.hives_collection.find_one({"_id": util.str_to_objectid(sensor['beehive_id'])})
                            if hive and hive.get('farm_id'):
                                farm = mongo.farms_collection.find_one({"_id": util.str_to_objectid(hive['farm_id'])})

                    # Build the event message
                    predator_type = predator_result.predator or "unknown predator"
                    confidence_pct = int(predator_result.confidence * 100)

                    event = {
                        "alertType": "predator_detected",
                        "severity": "critical",
                        "title": "Predator Detected!",
                        "message": f"A {predator_type} has been detected with {confidence_pct}% confidence. Defense systems activated.",
                        "imageId": str(result.inserted_id),
                        "details": {
                          "predatorDetectionMethod": predator_result.details.get("description")
                        },
                        "timestampMs": datetime.now(timezone.utc)
                    }

                    # Add contextual information if available
                    if sensor:
                        event["sensorName"] = sensor.get('name', 'Unknown Sensor')
                    if hive:
                        event["beehiveName"] = hive.get('name', 'Unknown Beehive')
                    if farm:
                        event["farmName"] = farm.get('name', 'Unknown Farm')

                    # Send the event to SSE queue
                    enqueue_sse(event)
                    logger.info(f"Predator detection alert sent: {predator_type} at {event.get('farmName', 'Unknown location')}")
                except Exception as e:
                    logger.error(f"Failed to send predator detection notification: {str(e)}")
                    traceback.print_exc()

        if bee_count_result is not None:
            response['bee_count'] = image_doc['bee_count']

        if honeypot_result is not None:
            response['honeypot_analysis'] = image_doc['honeypot_analysis']

        return jsonify(response), 201
    except Exception as e:
        logger.error(f"Failed to save image: {str(e)}")
        return jsonify({'error': f'Failed to save image: {str(e)}'}), 500


@app.route('/api/images', methods=['GET'])
def get_latest_image():
    """
    Endpoint to retrieve the latest uploaded image.
    Accepts optional query parameters:
    - beehive_id: Filter images by beehive (via sensor_id lookup)
    - context: Filter images by context (defense, data_collection, harvest)
    """
    logger.info(f"Received GET request to /api/images from {request.remote_addr}")

    try:
        # Get query parameters
        beehive_id = request.args.get('beehive_id')
        context = request.args.get('context')

        # Build the query filter
        query_filter = {}

        # Filter by context if provided
        if context:
            query_filter['context'] = context

        # Filter by beehive_id if provided (need to lookup sensor_id first)
        if beehive_id:
            # Find all sensors for this beehive
            sensors = list(mongo.sensors_collection.find({"beehive_id": beehive_id}))
            if sensors:
                sensor_ids = [util.objectid_to_str(sensor['_id']) for sensor in sensors]
                query_filter['sensor_id'] = {'$in': sensor_ids}
            else:
                # No sensors found for this beehive, return empty result
                logger.warning(f"No sensors found for beehive_id: {beehive_id}")
                return jsonify({'error': 'No sensors found for the specified beehive'}), 404

        # Find the latest image matching the filter
        image_doc = mongo.image_collection.find_one(
            query_filter,
            sort=[('upload_time', -1)]  # Sort by upload_time descending to get latest
        )

        if not image_doc:
            logger.warning(f"No image found matching filter: {query_filter}")
            return jsonify({'error': 'No image found matching the criteria'}), 404

        # Build response with metadata
        response = {
            'id': str(image_doc['_id']),
            'filename': image_doc.get('filename'),
            'sensor_id': image_doc.get('sensor_id'),
            'content_type': image_doc.get('content_type'),
            'upload_time': image_doc.get('upload_time').isoformat() if image_doc.get('upload_time') else None,
            'context': image_doc.get('context')
        }

        # Include predator analysis if available
        if 'predator_analysis' in image_doc:
            response['predator_analysis'] = image_doc['predator_analysis']
            # Convert analyzed_at to ISO format if present
            if 'analyzed_at' in response['predator_analysis']:
                response['predator_analysis']['analyzed_at'] = response['predator_analysis']['analyzed_at'].isoformat()

        # Include bee count if available
        if 'bee_count' in image_doc:
            response['bee_count'] = image_doc['bee_count']
            # Convert analyzed_at to ISO format if present
            if 'analyzed_at' in response['bee_count']:
                response['bee_count']['analyzed_at'] = response['bee_count']['analyzed_at'].isoformat()

        # Include honeypot analysis if available
        if 'honeypot_analysis' in image_doc:
            response['honeypot_analysis'] = image_doc['honeypot_analysis']
            # Convert analyzed_at to ISO format if present
            if 'analyzed_at' in response['honeypot_analysis']:
                response['honeypot_analysis']['analyzed_at'] = response['honeypot_analysis']['analyzed_at'].isoformat()

        # If the client wants the actual image data, include it as base64
        include_data = request.args.get('include_data', 'false').lower() == 'true'
        if include_data and 'data' in image_doc:
            import base64
            response['data'] = base64.b64encode(image_doc['data']).decode('utf-8')

        logger.info(f"Successfully retrieved latest image: {response['id']}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to retrieve latest image: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to retrieve latest image: {str(e)}'}), 500


@app.route('/api/images/<image_id>', methods=['GET'])
def get_image(image_id):
    """
    Endpoint to retrieve an image by its ID.
    Returns the image metadata and optionally the image data.
    """
    logger.info(f"Received GET request to /api/images/{image_id} from {request.remote_addr}")

    try:
        # Convert string ID to ObjectId
        from bson import ObjectId
        try:
            obj_id = ObjectId(image_id)
        except Exception as e:
            logger.warning(f"Invalid image ID format: {image_id}")
            return jsonify({'error': 'Invalid image ID format'}), 400

        # Find the image in MongoDB
        image_doc = mongo.image_collection.find_one({"_id": obj_id})

        if not image_doc:
            logger.warning(f"Image not found: {image_id}")
            return jsonify({'error': 'Image not found'}), 404

        # Build response with metadata
        response = {
            'id': str(image_doc['_id']),
            'filename': image_doc.get('filename'),
            'sensor_id': image_doc.get('sensor_id'),
            'content_type': image_doc.get('content_type'),
            'upload_time': image_doc.get('upload_time').isoformat() if image_doc.get('upload_time') else None,
            'context': image_doc.get('context')
        }

        # Include predator analysis if available
        if 'predator_analysis' in image_doc:
            response['predator_analysis'] = image_doc['predator_analysis']
            # Convert analyzed_at to ISO format if present
            if 'analyzed_at' in response['predator_analysis']:
                response['predator_analysis']['analyzed_at'] = response['predator_analysis']['analyzed_at'].isoformat()

        # Include bee count if available
        if 'bee_count' in image_doc:
            response['bee_count'] = image_doc['bee_count']
            # Convert analyzed_at to ISO format if present
            if 'analyzed_at' in response['bee_count']:
                response['bee_count']['analyzed_at'] = response['bee_count']['analyzed_at'].isoformat()

        # Include honeypot analysis if available
        if 'honeypot_analysis' in image_doc:
            response['honeypot_analysis'] = image_doc['honeypot_analysis']
            # Convert analyzed_at to ISO format if present
            if 'analyzed_at' in response['honeypot_analysis']:
                response['honeypot_analysis']['analyzed_at'] = response['honeypot_analysis']['analyzed_at'].isoformat()

        # If the client wants the actual image data, include it as base64
        include_data = request.args.get('include_data', 'false').lower() == 'true'
        if include_data and 'data' in image_doc:
            import base64
            response['data'] = base64.b64encode(image_doc['data']).decode('utf-8')

        logger.info(f"Successfully retrieved image {image_id}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to retrieve image: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to retrieve image: {str(e)}'}), 500


def monitor_sensor_heartbeat():
    logger.info("Starting sensor heartbeat monitoring task")

    sensors = list(mongo.sensors_collection.find({ "active": True}))
    logger.info(f"sensors found: {len(sensors)}")
    for sensor in sensors:
        data_types = (mongo.data_types_collection.find({"sensor_id": util.objectid_to_str(sensor["_id"])})
                     .sort("updated_at", -1)
                     .limit(1))
        data_type = next(data_types, None)
        if data_type and 'updated_at' in data_type and not data_type.get('data_type', '').startswith('honey_harvested'):
            try:
                last_sensor_update = datetime.fromtimestamp(int(data_type['updated_at'].replace(tzinfo=timezone.utc).timestamp()), timezone.utc)
                delta = datetime.now(timezone.utc) - last_sensor_update
                logger.info(f"sensor id: {sensor['_id']}, status: {sensor['status']}, last updated at {last_sensor_update.isoformat()} ({util.time_with_unit(delta.total_seconds())} ago)")
                if delta.total_seconds() > IDLE_TIME_TO_MARK_SENSOR_AS_OFFLINE and sensor['status'] == 'online':
                    logger.warning(f"Sensor {sensor['_id']} has not been updated {util.time_with_unit(delta.total_seconds())}")
                    mongo.sensors_collection.update_one({"_id": sensor['_id']}, {'$set': {'status': 'offline', 'updated_at': datetime.now(timezone.utc)}})
                    hive = mongo.hives_collection.find_one({"_id": util.str_to_objectid(sensor['beehive_id'])})
                    if hive is None:
                        event = {
                            "alertType": "offline_sensor",
                            "severity": "critical",
                            "title": "Sensor Non-Responsive",
                            "message": f"Sensor {sensor['name']} has been offline for more than {util.time_with_unit(delta.total_seconds())}.",
                            "timestampMs": datetime.now()
                        }
                    else:
                        farm = mongo.farms_collection.find_one({"_id": util.str_to_objectid(hive['farm_id'])})
                        event = {
                            "alertType": "offline_sensor",
                            "severity": "critical",
                            "title": "Sensor Non-Responsive",
                            "message": f"Sensor {sensor['name']} has been offline for more than {util.time_with_unit(delta.total_seconds())}.",
                            "beehiveId": util.objectid_to_str(hive['_id']),
                            "beehiveName": hive['name'],
                            "farmName": farm['name']
                        }
                    enqueue_sse(event)
                    continue # alert once per sensor
                elif delta.total_seconds() <= IDLE_TIME_TO_MARK_SENSOR_AS_OFFLINE and sensor['status'] == 'offline':
                    logger.info(f"Sensor {sensor['_id']} is now active")
                    mongo.sensors_collection.update_one({"_id": sensor['_id']}, {'$set': {'status': 'online', 'updated_at': datetime.now(timezone.utc)}})
                    hive = mongo.hives_collection.find_one({"_id": util.str_to_objectid(sensor['beehive_id'])})
                    if hive is None:
                        event = {
                            "alertType": "online_sensor",
                            "severity": "info",
                            "title": "Sensor is back online",
                            "message": f"Sensor {sensor['name']} is back online"
                        }
                    else:
                        farm = mongo.farms_collection.find_one({"_id": util.str_to_objectid(hive['farm_id'])})
                        event = {
                            "alertType": "online_sensor",
                            "severity": "info",
                            "title": "Sensor is back online",
                            "message": f"Sensor {sensor['name']} is back online",
                            "beehiveId": util.objectid_to_str(hive['_id']),
                            "beehiveName": hive['name'],
                            "farmName": farm['name']
                        }
                    enqueue_sse(event)
                    continue # alert once per sensor
            except Exception as e:
                logger.error(f"Failed to update sensor status: {str(e)}")
                logger.error(f'data_type: {data_type}')
                logger.error(f"Doc type: {type(data_type)}")
                logger.error(f"Doc keys: {list(data_type.keys())}")
                traceback.print_exc()
    logger.info("Completed sensor heartbeat monitoring task")

# Only start background tasks when running directly, not during tests
runner = None

def cleanup_background_tasks():
    """Cleanup function to gracefully shutdown background tasks"""
    global runner
    if runner:
        logger.info("Shutting down background tasks...")
        runner.shutdown(wait=True)
        runner = None
        logger.info("Background tasks shut down successfully")

if __name__ == '__main__':
    import os
    import atexit
    import signal

    # Only start background tasks in the main process (not the reloader process)
    # Flask's reloader spawns a child process, and we only want tasks in the child
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        runner = TaskRunner([(monitor_sensor_heartbeat, None, SENSOR_HEARTBEAT_FREQUENCY)])
        logger.info("Background tasks started")

        # Register cleanup handlers
        atexit.register(cleanup_background_tasks)

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            cleanup_background_tasks()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    try:
        logger.info(f"Starting Apiculture API on http://0.0.0.0:{API_PORT}")
        app.run(debug=True, host='0.0.0.0', port=API_PORT, use_reloader=True)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        traceback.print_exc()
    finally:
        cleanup_background_tasks()
