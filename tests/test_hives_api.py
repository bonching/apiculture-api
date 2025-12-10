import unittest
from datetime import datetime

from apiculture_api.app import app
import json


class TestHivesApi(unittest.TestCase):
    def setUp(self):
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True

    def test_save_hive(self):
        response = self.app.post(
            '/api/hives',
            data=json.dumps([
                {
                    'name': "Alpha Hive",
                    'description': "Main production hive with full monitoring",
                    'location': "North sector, Row 1, Position 1",
                    'farmId': "farm-1",
                    'harvestStatus': "excellent",
                    'honeyProduction': 45,
                    'sensorIds': ["sensor-1", "sensor-2", "sensor-3", "sensor-4", "sensor-5"],
                    'hasAlert': False,
                    'created_at': datetime.utcnow().isoformat(timespec='milliseconds')
                },
                {
                    'name': "Beta Hive",
                    'description': "Secondary hive with weather monitoring",
                    'location': "North sector, Row 1, Position 2",
                    'farmId': "farm-1",
                    'harvestStatus': "good",
                    'honeyProduction': 38,
                    'sensorIds': ["sensor-6", "sensor-7", "sensor-8"],
                    'hasAlert': False,
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

    def test_update_hive(self):
        response = self.app.put(
            '/api/hives/6934f297aa235a56488f3ba0',
            data=json.dumps({'description': 'Main production hive with full monitoring - test update'}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Hive updated successfully')
        self.assertIn('data', data)

    def test_get_hives(self):
        response = self.app.get('/api/hives')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 2)

    def test_delete_hive(self):
        response = self.app.delete('/api/hives/6937894152d8444820aae298')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Hive deleted successfully')
        self.assertIn('data', data)

if __name__ == '__main__':
    unittest.main()
