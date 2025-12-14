import unittest
from datetime import datetime, timezone

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
                    '_id': '693ad7c84739d5289a1e0833',
                    'name': "Alpha Hive",
                    'description': "Main production hive with full monitoring",
                    'location': "North sector, Row 1, Position 1",
                    'farmId': "693accdec9185a87bca56b00",
                    'harvestStatus': "excellent",
                    'honeyProduction': 45,
                    'sensorIds': [],
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                },
                {
                    '_id': '693ad7c84739d5289a1e0834',
                    'name': "Beta Hive",
                    'description': "Secondary hive with weather monitoring",
                    'location': "North sector, Row 1, Position 2",
                    'farmId': "693accdec9185a87bca56b00",
                    'harvestStatus': "good",
                    'honeyProduction': 38,
                    'sensorIds': [],
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                },
                {
                    '_id': '693ad7c84739d5289a1e0835',
                    'name': "Gamma Hive",
                    'description': "Observation hive with image capture",
                    'location': "South sector, Row 2, Position 3",
                    'farmId': "693accdec9185a87bca56b00",
                    'harvestStatus': "fair",
                    'honeyProduction': 32,
                    'sensorIds': [],
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                }
            ]),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('data', data)


        response = self.app.post(
            '/api/hives',
            data=json.dumps([
                {
                    '_id': '693ad7c84739d5289a1e0836',
                    'name': "Delta Hive",
                    'description': "High-production hive with pollen monitoring",
                    'location': "East sector, Row 1, Position 1",
                    'farmId': "693accdec9185a87bca56b01",
                    'harvestStatus': "excellent",
                    'honeyProduction': 52,
                    'sensorIds': [],
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                },
                {
                    '_id': '693ad7c84739d5289a1e0837',
                    'name': "Epsilon Hive",
                    'description': "Maintenance required - sensors offline",
                    'location': "West sector, Row 3, Position 2",
                    'farmId': "693accdec9185a87bca56b01",
                    'harvestStatus': "poor",
                    'honeyProduction': 18,
                    'sensorIds': [],
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                }
            ]),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('data', data)


        response = self.app.post(
            '/api/hives',
            data=json.dumps([
                {
                    '_id': '693ad7c84739d5289a1e0838',
                    'name': "Zeta Hive",
                    'description': "Advanced monitoring with multi-spectrum analysis",
                    'location': "Central sector, Row 1, Position 1",
                    'farmId': "693accdec9185a87bca56b02",
                    'harvestStatus': "good",
                    'honeyProduction': 41,
                    'sensorIds': [],
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')
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
            '/api/hives/693ad7c84739d5289a1e0838',
            data=json.dumps({'description': 'Advanced monitoring with multi-spectrum analysis - update'}),
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
        response = self.app.delete('/api/hives/693ad7c84739d5289a1e0838')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Hive deleted successfully')
        self.assertIn('data', data)

if __name__ == '__main__':
    unittest.main()
