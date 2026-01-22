import random
import sys
import time
from pathlib import Path

import requests

from apiculture_api.util.app_util import AppUtil
from apiculture_api.util.config import API_HOST, API_PORT

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
        logging.FileHandler('../apiculture-api.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('defense_simulator')
logger.setLevel(logging.INFO)

class DefenseSimulator:
    """
    Simulates predator detection by uploading images from the bee_predators folder
    to the API server, which triggers:
    1. Predator analysis
    2. Sprinkler activation
    3. SSE alert notification to connected clients
    """

    def __init__(self):
        # Get path to predator images
        self.images_dir = Path(__file__).parent / "images" / "bee_predators"
        if not self.images_dir.exists():
            logger.error(f"Predator images directory not found: {self.images_dir}")
            raise FileNotFoundError(f"Directory not found: {self.images_dir}")

        # Get list of predator images
        self.predator_images = list(self.images_dir.glob("*.jpg")) + list(self.images_dir.glob("*.png"))
        if not self.predator_images:
            logger.error(f"No predator images found in directory: {self.images_dir}")
            raise FileNotFoundError(f"No predator images found in directory: {self.images_dir}")

        logger.info(f"Found {len(self.predator_images)} predator images in: {self.images_dir}")

    def run(self, interval_seconds=30, max_runs=None):
        """
        Run the defense simulator.

        Args:
             interval_seconds: Time to wait between simulations (default: 30 seconds)
             max_runs: Maximum number of runs (None = run indefinitely)
        """
        # Get sensors with defense capability
        sensors = list(mongo.sensors_collection.find({
            'active': True,
            'data_capture': 'image'
        }))

        if not sensors:
            logger.warning("No active image capture sensors found in database")
            logger.info("The simulator will still run and upload images without sensor context")
        else:
            logger.info(f"Found {len(sensors)} active image capture sensors")

        run_count = 0

        try:
            while True:
                run_count += 1

                if max_runs and run_count >= max_runs:
                    logger.info(f"Reached maximum runs ({max_runs}). Stopping simulator.")
                    break

                logger.info(f"\n{'='*80}")
                logger.info(f"Defense Simulation Run #{run_count}")
                logger.info(f"{'='*80}")

                # Randomly select a predator image
                selected_image = random.choice(self.predator_images)
                logger.info(f"Selected predator image: {selected_image.name}")

                # Randomly select a sensor if available
                sensor_id = None
                sensor_name = "unknown"
                if sensors:
                    sensor = random.choice(sensors)
                    sensor_id = util.objectid_to_str(sensor["_id"])
                    sensor_name = sensor.get('name', 'Unknown')
                    logger.info(f"Using sensor: {sensor_name} (ID: {sensor_id})")

                # Upload the image to the server
                result = self.upload_defense_image(selected_image, sensor_id)

                if result:
                    logger.info(f"Defense simulation completed successfully")
                    self._log_result(result)
                else:
                    logger.error(f"Defense simulation failed")

                # Wait before next simulation (unless this was the last run)
                if not max_runs or run_count < max_runs:
                    logger.info(f"Waiting {interval_seconds} seconds before next simulation...")
                    time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("\n\nDefense simulator stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Unexpected error in defense simulator: {str(e)}")
            raise

    def upload_defense_image(self, image_path, sensor_id=None):
        """
        Upload a defense image to the API server.

        Args:
             image_path: Path to the image file
             sensor_id: Optional sensor ID

        Returns:
            Response data dict or None on failure
        """
        try:
            # Prepare the multipart form data
            with open(image_path, 'rb') as image_file:
                files = {
                    'image': (f"defense_{image_path.name}", image_file, 'image/jpeg')
                }

                data = {
                    'context': 'defense'
                }

                if sensor_id:
                    data['sensor_id'] = sensor_id

                # POST to the image upload endpoint
                url = f"http://{API_HOST}:{API_PORT}/api/images"
                logger.info(f"POST {url}")
                logger.info(f"   - Image: {image_path.name}")
                logger.info(f"   - Context: defense")
                if sensor_id:
                    logger.info(f"   - Sensor ID: {sensor_id}")

                response = requests.post(url, files=files, data=data, timeout=30)

                if response.status_code == 201:
                    result = response.json()
                    logger.info(f"Server responded with status 201 Created")
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
            logger.error(f"Error uploading image: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _log_result(self, result):
        """Log the result of teh defense simulation."""
        logger.info(f"\nResult:")
        logger.info(f"  - Image ID: {result.get('inserted_id')}")
        logger.info(f"  - Filename: {result.get('filename')}")

        if 'predator_analysis' in result:
            analysis = result['predator_analysis']
            logger.info(f"\n  Predator Analysis:")
            logger.info(f"    - Detected: {analysis.get('predator_detected')}")
            logger.info(f"    - Confidence: {analysis.get('confidence', 0):.1%}")
            logger.info(f"    - Predator: {analysis.get('predator', 'None')}")

            if 'details' in analysis:
                details = analysis['details']
                logger.info(f"    - Method: {details.get('method', 'unknown')}")
                logger.info(f"    - Wasp Score: {details.get('wasp_score', 0):.2%}")

        if 'run_sprinkler' in result:
            logger.info(f"\n  Defense Action:")
            logger.info(f"  - Sprinkler Activated: {result['run_sprinkler']}")
            logger.info(f"  - ALERT SENT TO BEEKEEPERS VIA SSE")

    def run_once(self, image_name=None, sensor_id=None):
        """
        Run a single defense simulation.

        Args:
             image_name: Optional specific image name to use (otherwise random)
             sensor_id: Optional sensor ID to use

        Returns:
            Response data dict or None on failure
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Single Defense Simulation")
        logger.info(f"{'='*80}")

        # Select image
        if image_name:
            selected_image = self.images_dir / image_name
            if not selected_image.exists():
                logger.error(f"Image not found: {selected_image}")
                return None
        else:
            selected_image = random.choice(self.predator_images)

        logger.info(f"Selected predator image: {selected_image.name}")

        # Get sensor if not provided
        if not sensor_id:
            sensors = list(mongo.sensors_collection.find({
                'active': True,
                'data_capture': 'image'
            }))
            if sensors:
                sensor = random.choice(sensors)
                sensor_id = util.objectid_to_str(sensor["_id"])
                logger.info(f"Using sensor: {sensor.get('name')} (ID: {sensor_id})")

        # Upload the image
        result = self.upload_defense_image(selected_image, sensor_id)

        if result:
            logger.info(f"\n Defense simulation completed successfully")
            self._log_result(result)
        else:
            logger.error(f"\n Defense simulation failed")

        return result


if __name__ == "__main__":
    """
    Run the defense simulator.
    
    Usage:
        # Run once with random image
        python -m apiculture_api.simulator.defense_simulator
        
        # Run continuously (every 30 seconds)
        python -m apiculture_api.simulator.defense_simulator --continuous
        
        # Run with custom interval
        python -m apiculture_api.simulator.defense_simulator --continuous --interval 60
        
        # Run specific number of times
        python -m apiculture_api.simulator.defense_simulator --continuous --runs 5
    """
    import argpase

    parser = argpase.ArgumentParser(description='Defense Simulator - Simulates predator detection')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuously instead of once')
    parser.add_argument('--interval', type=int, default=30,
                        help='Seconds between simulations (default: 30 seconds)')
    parser.add_argument('--runs', type=int, default=None,
                        help='Maximum number of runs (default: infinite)')
    parser.add_argument('--image', type=str, default=None,
                        help='Specific image filename to use')
    parser.add_argument('--sensor-id', type=str, default=None,
                        help='Specific sensor ID to use')

    args = parser.parse_args()

    simulator = DefenseSimulator()

    if args.continuous:
        simulator.run(interval_seconds=args.interval, max_runs=args.runs)
    else:
        simulator.run_once(image_name=args.image, sensor_id=args.sensor_id)
