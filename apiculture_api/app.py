import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone

from apiculture_api.api.farms_api import farms_api
from apiculture_api.api.hives_api import hives_api
from apiculture_api.api.sensors_api import sensors_api
from apiculture_api.api.metrics_api import metrics_api
from apiculture_api.alerts_api import alerts_api, enqueue_sse

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import SENSOR_HEARTBEAT_FREQUENCY
from apiculture_api.util.task_runner import TaskRunner

util = AppUtil()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('app')
logger.setLevel(logging.INFO)

# Create the Flask application
app = Flask(__name__)
app.register_blueprint(farms_api)
app.register_blueprint(hives_api)
app.register_blueprint(sensors_api)
app.register_blueprint(metrics_api)
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
    Stores the image as binary data in the MongoDB 'images' collection.
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

    try:
        # Read image as binary
        image_data = image_file.read()
        # Create document with image data and metadata
        image_doc = {
            'filename': image_file.filename,
            'data': image_data,
            'content_type': image_file.content_type,
            'upload_time': datetime.now(timezone.utc)
        }
        # Insert into MongoDB
        result = mongo.image_collection.insert_one(image_doc)
        logger.info(f"Successfully saved image {image_file.filename} with ID: {result.inserted_id}")
        return jsonify({
            'message': 'Image uploaded successfully',
            'inserted_id': str(result.inserted_id),
            'filename': image_file.filename
        }), 201
    except Exception as e:
        logger.error(f"Failed to save image: {str(e)}")
        return jsonify({'error': f'Failed to save image: {str(e)}'}), 500


def monitor_sensor_heartbeat():
    sensors = list(mongo.sensors_collection.find({ "active": True}))
    for sensor in sensors:
        data_types = (mongo.data_types_collection.find({"sensor_id": util.objectid_to_str(sensor["_id"])}, {"updated_at": 1, "beehive_id": 1})
                     .sort("updated_at", -1)
                     .limit(1))
        data_type = next(data_types, None)
        if data_type and 'updated_at' in data_type:
            try:
                last_sensor_update = datetime.fromtimestamp(int(data_type['updated_at'].replace(tzinfo=timezone.utc).timestamp()), timezone.utc)
                delta = datetime.now(timezone.utc) - last_sensor_update
                if delta.total_seconds() > 60 * 5 and sensor['status'] == 'online':
                    logger.warning(f"Sensor {sensor['_id']} has not been updated in the last 5 minutes")
                    mongo.sensors_collection.update_one({"_id": sensor['_id']}, {'$set': {'status': 'offline', 'updated_at': datetime.now(timezone.utc)}})
                elif delta.total_seconds() <= 60 * 5 and sensor['status'] == 'offline':
                    logger.info(f"Sensor {sensor['_id']} is now active")
                    mongo.sensors_collection.update_one({"_id": sensor['_id']}, {'$set': {'status': 'online', 'updated_at': datetime.now(timezone.utc)}})
                    hive = mongo.hives_collection.find_one({"_id": util.str_to_objectid(sensor['beehive_id'])})
                    if hive is None:
                        event = {
                          "severity": "info",
                          "title": "Sensor is back online",
                          "message": f"Sensor {sensor['name']} is back online",
                          "timestamp": "just now",
                          "timestampMs": datetime.now().isoformat(timespec='milliseconds')
                        }
                    else:
                        farm = mongo.farms_collection.find_one({"_id": util.str_to_objectid(hive['farm_id'])})
                        event = {
                          "severity": "info",
                          "title": "Sensor is back online",
                          "message": f"Sensor {sensor['name']} is back online",
                          "beehiveName": hive['name'],
                          "farmName": farm['name'],
                          "timestamp": "just now",
                          "timestampMs": datetime.now().isoformat(timespec='milliseconds')
                        }
                    enqueue_sse(event)
            except Exception as e:
                logger.error(f"Failed to update sensor status: {str(e)}")
                logger.error(f'data_type: {data_type}')
                logger.error(f"Doc type: {type(data_type)}")
                logger.error(f"Doc keys: {list(data_type.keys())}")
                traceback.print_exc()

runner = TaskRunner([(monitor_sensor_heartbeat, None, SENSOR_HEARTBEAT_FREQUENCY)])

if __name__ == '__main__':
    try:
        logger.info("Starting Apiculture API on http://0.0.0.0:8080")
        app.run(debug=True, host='0.0.0.0', port=8080)
    finally:
        runner.shutdown(wait=True)
