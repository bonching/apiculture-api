import unittest
from datetime import datetime, timezone

from apiculture_api.app import app
import json


class TestApicultureApi(unittest.TestCase):
    def setUp(self):
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True

        # Sample valid sensor data
        self.valid_data = {
            'temperature': 25.5,
            'humidity': 60,
            'timestamp': '2025-08-27T12:27:00'
        }

        # Invalid data (non-JSON)
        self.invalid_data = "not a json string"

    def test_post_valid_sensor_data(self):
        """Test POST request with valid JSON data."""
        response = self.app.post(
            '/api/sensor-data',
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('inserted_id', data)

    def test_post_no_json_data(self):
        """Test POST request with non-JSON content."""
        response = self.app.post(
            '/api/sensor-data',
            data=self.invalid_data,
            content_type='text/plain'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Request must be JSON')

    def test_post_empty_json(self):
        """Test POST request with empty JSON body."""
        response = self.app.post(
            '/api/sensor-data',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'No data provided')

    def test_bee_counter_image_upload(self):
        """Test POST request to /api/images endpoint with bee image for counting."""
        import os
        from apiculture_api.util.mongo_client import ApicultureMongoClient
        from apiculture_api.util.app_util import AppUtil

        # Get the path to the test image
        image_path = os.path.join('images', 'bee', 'bee.jpg')

        # Check if image exists
        if not os.path.exists(image_path):
            self.skipTest(f"Image {image_path} does not exist")

        mongo = ApicultureMongoClient()
        util = AppUtil()

        sensor_id = '693b4c90943e75b9d619e11b'

        # Verify bee_count data type exists
        data_type = mongo.data_types_collection.find_one({
            'sensor_id': sensor_id,
            'data_type': 'bee_count'
        })
        if not data_type:
            self.skipTest("bee_count data_type not found for sensor")

        # Open and read the image file
        with open(image_path, 'rb') as img_file:
            response = self.app.post(
                '/api/images',
                data={
                    'image': (img_file, 'bee.jpg', 'image/jpeg'),
                    'context': 'data_collection',
                    'sensor_id': sensor_id
                },
                content_type='multipart/form-data'
            )

            data = json.loads(response.data)

        # Assert successful upload
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Image uploaded successfully')
        self.assertIn('inserted_id', data)
        self.assertIn('filename', data)
        self.assertEqual(data['filename'], 'bee.jpg')

        # Assert bee count result is present
        self.assertIn('bee_count', data)
        self.assertIn('count', data['bee_count'])
        self.assertIn('confidence', data['bee_count'])
        self.assertIsInstance(data['bee_count']['count'], int)
        self.assertIsInstance(data['bee_count']['confidence'], (int, float))

        # Verify metric was saved to database
        data_type_id = util.objectid_to_str(data_type['_id'])
        metric = mongo.metrics_collection.find_one(
            {'data_type_id': data_type_id},
            sort=[('datetime', -1)] # Get most recent
        )
        self.assertIsNotNone(metric, "Bee count metric should be saved to database")
        self.assertEqual(metric['value'], data['bee_count']['count'], "Metric value should match bee count")

    def test_defense_image_upload(self):
        """Test POST request to /api/images endpoint with image for predator analysis."""
        import os
        import random
        from apiculture_api.util.mongo_client import ApicultureMongoClient
        from apiculture_api.util.app_util import AppUtil

        # Get path to bee_predators folder
        predators_folder = os.path.join('images', 'bee_predators')

        # Check if folder exists
        if not os.path.exists(predators_folder):
            self.skipTest(f"Folder {predators_folder} does not exist")

        # Get all image files in the folder
        image_files = [f for f in os.listdir(predators_folder)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]

        if not image_files:
            self.skipTest(f"No image files found in {predators_folder}")

        # Randomly select an image
        selected_image = random.choice(image_files)
        image_path = os.path.join(predators_folder, selected_image)

        print(f"Testing with randomly selected image: {selected_image}")

        # Determine content type based on file extension
        ext = selected_image.lower().rsplit('.',1)[-1]
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif'
        }
        content_type = content_type_map.get(ext, 'image/jpeg')

        # Open and read the image file
        with open(image_path, 'rb') as img_file:
            response = self.app.post(
                '/api/images',
                data={
                    'image': (img_file, selected_image, content_type),
                    'context': 'defense'
                },
                content_type='multipart/form-data'
            )

        data = json.loads(response.data)

        # Assert successful upload
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Image uploaded successfully')
        self.assertIn('inserted_id', data)
        self.assertIn('filename', data)
        self.assertEqual(data['filename'], selected_image)

        # Assert predator analysis result is present
        self.assertIn('predator_analysis', data)
        self.assertIn('predator_detected', data['predator_analysis'])
        self.assertIn('confidence', data['predator_analysis'])
        self.assertIn('predator', data['predator_analysis'])
        self.assertIsInstance(data['predator_analysis']['predator_detected'], bool)
        self.assertIsInstance(data['predator_analysis']['confidence'], (int, float))

        # If predator is detected, run_sprinkler should be 'Y'
        if data['predator_analysis']['predator_detected']:
            self.assertIn('run_sprinkler', data)
            self.assertEqual(data['run_sprinkler'], 'Y')
            print(f"Predator detected: {data['predator_analysis']['predator']} "
                  f"with confidence {data['predator_analysis']['confidence']}")
        else:
            print(f"No predator detected (confidence: {data['predator_analysis']['confidence']})")

    def _generate_random_temperature(self):
        return {
            'temperature': 25.5,
            'timestamp': datetime.now(timezone.utc),
        }


if __name__ == '__main__':
    unittest.main()