import unittest
from datetime import datetime

from apiculture_api.app import app
import json


class TestFarmsApi(unittest.TestCase):
    def setUp(self):
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True

    def test_save_farm(self):
        response = self.app.post(
            '/api/farms',
            data=json.dumps([
                {
                    'farm_id': 1,
                    'name': 'Ising Farm',
                    'description': 'Main production farm with advanced monitoring systems',
                    'address': 'Calangcawan Sur, Vinzons, Camarines Norte'
                }
            ]),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('inserted_id', data)


    def _generate_random_temperature(self):
        return {
            'temperature': 25.5,
            'timestamp': datetime.utcnow().isoformat(timespec='milliseconds'),
        }

if __name__ == '__main__':
    unittest.main()