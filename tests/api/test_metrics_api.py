import unittest
from datetime import datetime, timezone, timedelta
import random

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
                    'datetime': datetime.now(timezone.utc).isoformat(),
                    'dataTypeId': "693d6f2dd8f5aae43d541acd",
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

    def test_save_and_Get_honey_harvested_metrics(self):
        """Test saving and retrieving honey harvested metrics with data spanning past 5 years."""
        beehive_id = '693ad7c84739d5289a1e0835'  # Gamma beehive
        sensor_id = '693b4c90943e75b9d619e11c'

        # Derive data_type_id for this sensor and data_capture (seed DBs may or may not scope data_types by sensor_id)
        from apiculture_api.util.mongo_client import ApicultureMongoClient
        from apiculture_api.util.app_util import AppUtil
        util = AppUtil()
        mongo = ApicultureMongoClient()
        try:
            data_type = (
                mongo.data_types_collection.find_one({'sensor_id': sensor_id, 'data_type': 'honey_harvested'})
                or mongo.data_types_collection.find_one({'data_type': 'honey_harvested'})
            )
            self.assertIsNotNone(
                data_type, (
                    "No data_types record found for honey harvest; tried: "
                    "(sensor_id + honey_harvested), (global honey_harvested)"
                )
            )
            data_type_id = util.objectid_to_str(data_type['_id'])
        finally:
            mongo.close()

        # Generate dummy data for the past 5 years (60 months)
        # Create entries for each 4-month period
        metrics_data = []
        now = datetime.now(timezone.utc)

        # Generate data for 15 periods (5 years = 60 months / 4 = 15 periods)
        for period in range (15):
            # Calculate months ago for this period
            months_ago_start = period * 4
            months_ago_end = (period + 1) * 4

            # Add 2-3 entries per period to simulate multiple harvests
            for entry in range(2):
                # Calculate a date within this period
                months_offset = months_ago_start + (entry * 1)

                # Create a datetime by subtracting months
                # Approximate: 30 days per month
                days_offset = months_offset *30
                entry_date = now - timedelta(days=days_offset)

                # Vary the harvest amounts (50-150 kg range)
                value = round(50 + random.random() * 100, 1)

                metrics_data.append({
                    'datetime': entry_date.isoformat(),
                    'dataTypeId': sensor_id,
                    'beehiveId': beehive_id,
                    'value': value
                })

        # Post all metrics data
        response = self.app.post(
            '/api/metrics',
            data=json.dumps(metrics_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Data saved successfully')
        self.assertIn('data', data)

        # Verify we saved 30 entries (15 periods * 2 entries)
        self.assertEqual(len(data['data']), 30)

        print(f"\n Successfully inserted {len(metrics_data)} honey harvest metrics spanning 5 years.")

        # Now test GET endpoint
        response = self.app.get(f'/api/metrics/{beehive_id}/honey_harvested')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)

        # Should return 15 periods (5 years / 4 months each)
        periods = data['data']
        self.assertEqual(len(periods), 15)

        # Verify the structure of returned data
        for period in periods:
            self.assertIn('datetime', period)
            self.assertIn('value', period)
            # Time should be in format "0mo", "4mo", "8mo", etc."
            self.assertTrue(period['time'].endswith('mo'))

        # API returns oldest -> newest (56mo ... 0mo)
        self.assertEqual(periods[0]['time'], '56mo')

        # Last period should be "0mo" (most recent 4 months)
        self.assertEqual(periods[-1]['time'], '0mo')

        print(f"\n Successfully retrieved {len(periods)}  4-month periods of honey harvest data.")
        print(f"   Time range: {periods[0]['time']} - {periods[-1]['time']}")
        print(f"   Sample data: {periods[0]}")


    def test_get_metrics(self):
        response = self.app.get('/api/metrics/693ad7c84739d5289a1e0833/temperature')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)

if __name__ == '__main__':
    unittest.main()
