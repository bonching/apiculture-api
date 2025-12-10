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
                    'dataCapture': ["temperature", "humidity"],
                    'status': "online",
                    'beehiveId': "6937894152d8444820aae298",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.utcnow().isoformat(timespec='milliseconds')
                },
                {
                    'name': "MEMS Acoustic Monitor",
                    'dataCapture': ["sound", "vibration"],
                    'status': "online",
                    'beehiveId': "6937894152d8444820aae298",
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

    def test_sensor_add_data_type(self):
        response = self.app.put(
            '/api/sensors/6938de0b4894fe4e61a531d3',
            data=json.dumps({
                'name': "Bosch BME680 Env Sensor - test add data type",
                'dataCapture': ["temperature", "humidity", "co2", "voc"]
            }),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Sensor updated successfully')
        self.assertIn('data', data)

    def test_sensor_remove_data_type(self):
        response = self.app.put(
            '/api/sensors/6938de0b4894fe4e61a531d3',
            data=json.dumps({
                'name': "Bosch BME680 Env Sensor - test remove data type",
                'dataCapture': ["temperature", "humidity", "co2"]
            }),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Sensor updated successfully')
        self.assertIn('data', data)

    def test_sensor_add_previous_data_type(self):
        response = self.app.put(
            '/api/sensors/6938de0b4894fe4e61a531d3',
            data=json.dumps({
                'name': "Bosch BME680 Env Sensor - test add previous data type",
                'dataCapture': ["temperature", "humidity", "co2", "voc"]
            }),
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

    def test_delete_sensor(self):
        response = self.app.delete('/api/sensors/6938de0b4894fe4e61a531d4')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Sensor deleted successfully')
        self.assertIn('data', data)

if __name__ == '__main__':
    unittest.main()
