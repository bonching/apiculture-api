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
                    'name': 'Ising Farm',
                    'description': 'Main production farm with advanced monitoring systems',
                    'address': 'Calangcawan Sur, Vinzons, Camarines Norte',
                    'beehiveIds': [],
                    'created_at': datetime.utcnow().isoformat(timespec='milliseconds')
                },
                {
                    'name': 'Alveare Farm',
                    'description': 'Organic certified farm specializing in quality honey production',
                    'address': 'Calangcawan Sur, Vinzons, Camarines Norte',
                    'beehiveIds': [],
                    'created_at': datetime.utcnow().isoformat(timespec='milliseconds')
                },
                {
                    'name': 'BoJayHan Farm',
                    'description': 'Research and development apiary with experimental hives',
                    'address': 'Iberica, Labo, Camarines Norte',
                    'beehiveIds': [],
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

    def test_update_farm(self):
        response = self.app.put(
            '/api/farms/6927b669aff0f0ee8358c04c',
            data=json.dumps({'description': 'Main production farm with advanced monitoring systems'}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Farm updated successfully')
        self.assertIn('data', data)

    def test_get_farms(self):
        response = self.app.get('/api/farms')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 3)

    def test_delete_farm(self):
        response = self.app.delete('/api/farms/6937885ce4e485b7a9e2e626')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Farm deleted successfully')
        self.assertIn('data', data)

if __name__ == '__main__':
    unittest.main()
