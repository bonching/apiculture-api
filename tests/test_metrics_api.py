import unittest
from datetime import datetime

from apiculture_api.app import app
import json


class TestMetricsApi(unittest.TestCase):
    def setUp(self):
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True

    def test_save_metric(self):
        response = self.app.post(
            '/api/metrics',
            data=json.dumps([
                {
                    'datetime': datetime.utcnow().isoformat(timespec='milliseconds'),
                    'dataTypeId': "6936e531c0169bd88beeda6b",
                    'value': 34.5
                }
            ]),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('data', data)

    def test_get_metrics(self):
        response = self.app.get('/api/metrics')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 1)

if __name__ == '__main__':
    unittest.main()
