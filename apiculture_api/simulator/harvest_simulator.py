import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import DATA_COLLECTION_METRICS, API_HOST, API_PORT

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
    ]
)
logger = logging.getLogger('harvest_simulator')
logger.setLevel(logging.INFO)

class HarvestSimulator:

    def __init__(self):
        pass

    def run(self):
        sensor_id = '693b4c90943e75b9d619e139' # this sensor is not attached to any beehive (harvest sensor)
        beehive_id = '693ad7c84739d5289a1e0835'

        # UPload honeypot image and capture the result
        upload_result = self.upload_honeypots_image(sensor_id=sensor_id)

        # Extract imageId from upload result
        image_id = None
        if upload_result:
            image_id = upload_result.get('imageId', upload_result.get('inserted_id'))
            if image_id:
                logger.info(f"Captured imageId from upload: {image_id}")

        # Query the data_types collection to get the honey_harvested data type ID
        data_type = mongo.data_types_collection.find_one({
            'sensor_id': sensor_id,
            'data_type': 'honey_harvested'
        })

        if not data_type:
            logger.info(f"Could not find honey_harvested data type for sensor {sensor_id}")
            return

        data_type_id = util.objectid_to_str(data_type['_id'])
        logger.info(f"Found honey_harvested data type ID: {data_type_id}")

        base_value = DATA_COLLECTION_METRICS['honey_harvested']['base_value']
        variance = DATA_COLLECTION_METRICS['honey_harvested']['variance']

        value = round(base_value + (random.random() * variance) * 10) / 10
        data = [
            {
                'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                'dataTypeId': data_type_id,
                'beehiveId': beehive_id,
                'value': value,
                'imageId': image_id  # Include imageId from honeypot analysis
            }
        ]
        logger.info(f'Honey harvested: {str(data)}')
        response = requests.post(f'http://{API_HOST}:{API_PORT}/api/metrics', json=data)
        logger.info(response.json())

    def upload_honeypots_image(self, image_path=None, sensor_id=None):
        """
        Uploads a honeypots image to the API.
        If image_path is empty, selects a random image from /images/honeypots folder.

        Args:
             image_path: Path to the image file (empty string = select random)
             sensor_id: Optional sensor ID

        Returns:
            Response data dict or None on failure
        """
        try:
            # If no image path provided, select random image from honeypots folder
            if not image_path or image_path == '':
                honeypots_path = Path(__file__).parent.parent / 'images' / 'honeypots'

                if not honeypots_path.exists():
                    logger.error(f"Honeypots image directory not found: {honeypots_path}")
                    return None

                # Get list of honeypot images
                honeypots_images = list(honeypots_path.glob("*.jpg")) + \
                                    list(honeypots_path.glob("*.jpeg")) + \
                                    list(honeypots_path.glob("*.png"))

                if not honeypots_images:
                    logger.error(f"No honeypots images found in: {honeypots_path}")
                    return None

                # Select random image
                image_path = random.choice(honeypots_images)
                logger.info(f"Randomly selected honeypot image: {image_path.name}")
            else:
                image_path = Path(image_path)
                if not image_path.exists():
                    logger.error(f"Honeypot image not found: {image_path}")
                    return None

            # Prepare the multipart form data
            with open(image_path, 'rb') as img_file:
                files = {
                    'image': (f"harvest_{image_path.name}", img_file, 'image/jpeg')
                }

                data = {
                    'context': 'harvest'
                }

                if sensor_id:
                    data['sensorId'] = sensor_id

                # POST to the image upload endpoint
                url = f'http://{API_HOST}:{API_PORT}/api/images'
                logger.info(f"POST {url}")
                logger.info(f"   - Image: {image_path.name}")
                logger.info(f"   - Context: harvest")
                if sensor_id:
                    logger.info(f"   - Sensor ID: {sensor_id}")

                response = requests.post(url, files=files, data=data, timeout=30)

                if response.status_code == 201:
                    result = response.json()
                    logger.error(f"Server responded with status 201 Created")
                    self._log_honeypot_result(result)
                    return result
                else:
                    logger.error(f"Server responded with status {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return None

        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to server at http://{API_HOST}:{API_PORT}")
            logger.error(f"Make sure the API server is running!")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after 30 seconds")
            return None
        except Exception as e:
            logger.error(f"Error uploading honeypot image: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _log_honeypot_result(self, result):
        """Log the result of the honeypot analysis."""
        logger.info(f"\nResult:")
        logger.info(f"  - Image ID: {result.get('inserted_id')}")
        logger.info(f"  - Filename: {result.get('filename')}")

        if 'honey_analysis' in result:
            analysis = result['honey_analysis']
            logger.info(f"\nHoney Analysis:")
            logger.info(f"  - Honeypots Detected: {analysis.get('honey_detected')}")
            logger.info(f"  - Total Honeypots: {analysis.get('total_honeypots')}")
            logger.info(f"  - Filled: {analysis.get('filled_honeypots')}")
            logger.info(f"  - Empty: {analysis.get('empty_honeypots')}")
            logger.info(f"  - Fill Percentage: {analysis.get('fill_percentage')}%")
            logger.info(f"  - Confidence: {analysis.get('confidence', 0):.2%}")

            if 'details' in analysis:
                details = analysis['details']
                logger.info(f"  - Method: {details.get('method', 'unknown')}")
                logger.info(f"  - Description: {details.get('description', 'N/A')}")

            # Log grid analysis summary
            if 'grid_analysis' in analysis:
                grid = analysis['grid_analysis']
                logger.info(f"\n  Grid Analysis (3x3):")
                for position, data in grid.items():
                    if data.get('total', 0) > 0:
                        logger.info(f"    - {position.replace('_', ' ').title()}: "
                                    f"{data['filled']}/{data['total']} filled"
                                    f"({data['fill_percentage']:.%})")
            else:
                logger.warning(f"\n  No honeypot analysis in response")

if __name__ == '__main__':
    HarvestSimulator().run()
