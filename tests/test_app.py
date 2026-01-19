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

    def test_bee_counter_upload_image(self):
        """Test POST request to /api/images endpoint with bee image counting."""
        import os

        # Get the path to the test image
        image_path = os.path.join('images', 'bee', 'bee.jpg')

        # Check if image exists
        if not os.path.exists(image_path):
            self.skipTest(f"Image {image_path} does not exist")

        # Open and read the image file
        with open(image_path, 'rb') as image_file:
            response = self.app.post(
                '/api/images',
                data={
                    'image': (image_file, '1.jpg', 'image/jpeg'),
                    'context': 'data_collection'
                },
                content_type='multipart/form-data'
            )

            data = json.loads(response.data)

            # Assert successfully uploaded
            self.assertEqual(response.status_code, 201)
            self.assertIn('message', data)
            self.assertEqual(data['message'], 'Image uploaded successfully')
            self.assertIn('inserted_id', data)
            self.assertIn('filename', data)
            self.assertEqual(data['filename'], '1.jpg')

            # Assert bee count result is present
            self.assertIn('bee_count', data)
            self.assertIn('count', data['bee_count'])
            self.assertIn('confidence', data['bee_count'])
            self.assertIsInstance(data['bee_count']['count'], int)
            self.assertIsInstance(data['bee_count']['confidence'], (int, float))

    def _generate_random_temperature(self):
        return {
            'temperature': 25.5,
            'timestamp': datetime.now(timezone.utc),
        }


if __name__ == '__main__':
    unittest.main()