import unittest

from apiculture_api.app import app
import json


class TestAlertsApi(unittest.TestCase):
    def setUp(self):
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True

    def test_get_alerts(self):
        response = self.app.get('/api/alerts')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)

if __name__ == '__main__':
    unittest.main()
