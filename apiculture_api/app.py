import logging
from flask import Flask, request, jsonify
from pymongo import MongoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)

# Set up MongoDB connection (assuming local MongoDB instance)
try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client['apiculture']
    collection = db['sensor_readings']
    # Test MongoDB connection
    client.server_info()
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    exit(1)


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
        result = collection.insert_one(data)
        logger.info(f"Successfully saved data with ID: {result.inserted_id}")
        return jsonify({'message': 'Data saved successfully', 'inserted_id': str(result.inserted_id)}), 201
    except Exception as e:
        logger.error(f"Failed to save data: {str(e)}")
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500


if __name__ == '__main__':
    logger.info("Starting Apiculture API on http://0.0.0.0:8080")
    app.run(debug=True, host='0.0.0.0', port=8080)