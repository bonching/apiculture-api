import unittest
from datetime import datetime

from apiculture_api.app import app
import json


class TestSensorsApi(unittest.TestCase):
    def setUp(self):
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True

    def test_save_sensor(self):
        response = self.app.post(
            '/api/sensors',
            data=json.dumps([
                {
                    'name': "Bosch BME680 Env Sensor",
                    'dataCapture': ["temperature", "humidity", "co2", "voc"],
                    'status': "online",
                    'beehiveId': "69355f4d500745757044f8d9",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.utcnow().isoformat(timespec='milliseconds')
                },
                {
                    'name': "MEMS Acoustic Monitor",
                    'dataCapture': ["sound", "vibration"],
                    'status': "online",
                    'beehiveId': "69355f4d500745757044f8d9",
                    'hiveLocation': "brood",
                    'systems': ["data_collection", "defense"],
                    'created_at': datetime.utcnow().isoformat(timespec='milliseconds')
                }
            ]),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('data', data)

    def test_update_sensor(self):
        response = self.app.put(
            '/api/sensors/693692433b4b2eb130657057',
            data=json.dumps({'name': 'Bosch BME680 Env Sensor - test update'}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Sensor updated successfully')
        self.assertIn('data', data)

    def test_get_sensors(self):
        response = self.app.get('/api/sensors')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 2)

if __name__ == '__main__':
    unittest.main()
