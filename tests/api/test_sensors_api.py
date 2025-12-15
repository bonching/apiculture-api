import unittest
from datetime import datetime, timezone

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
                    '_id': '693ad7c84739d5289a1e0833',
                    'name': "Bosch BME680 Env Sensor",
                    'dataCapture': ["temperature", "humidity", "co2", "voc"],
                    'status': "online",
                    'currentValue': "34.5°C, 58%, 420ppm, 2.1kΩ",
                    'beehiveId': "693ad7c84739d5289a1e0833",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': '693ae983cbd27112179d9551',
                    'name': "MEMS Acoustic Monitor",
                    'dataCapture': ["sound", "vibration"],
                    'status': "online",
                    'currentValue': "68dB, 0.3mm/s",
                    'beehiveId': "693ad7c84739d5289a1e0833",
                    'hiveLocation': "brood",
                    'systems': ["data_collection", "defense"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': '693ae983cbd27112179d9552',
                    'name': "OpenCV AI Bee Counter",
                    'dataCapture': ["bee_count"],
                    'status': "online",
                    'currentValue': 45000,
                    'beehiveId': "693ad7c84739d5289a1e0833",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': '693ae983cbd27112179d9553',
                    'name': "TSL2591 Light & UV Sensor",
                    'dataCapture': ["lux", "uv_index"],
                    'status': "online",
                    'currentValue': "1200lux, UV4",
                    'beehiveId': "693ad7c84739d5289a1e0833",
                    'hiveLocation': "external",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': '693ae983cbd27112179d9554',
                    'name': "TGS2600 Chemical Sensor",
                    'dataCapture': ["pheromone", "odor_compounds"],
                    'status': "online",
                    'currentValue': "High",
                    'beehiveId': "693ad7c84739d5289a1e0833",
                    'hiveLocation': "brood",
                    'systems': ["data_collection", "defense"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e110",
                    'name': "Bosch BME280 Env Sensor",
                    'dataCapture': ["temperature", "humidity", "co2"],
                    'status': "online",
                    'currentValue': "33.8°C, 62%, 410ppm",
                    'beehiveId': "693ad7c84739d5289a1e0834",
                    'hiveLocation': "honey_super",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e111",
                    'name': "IR Beam Bee Counter",
                    'dataCapture': ["bee_count"],
                    'status': "online",
                    'currentValue': 42000,
                    'beehiveId': "693ad7c84739d5289a1e0834",
                    'hiveLocation': "honey_super",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e112",
                    'name': "Davis Vantage Weather Station",
                    'dataCapture': ["rainfall", "wind_speed", "barometric_pressure"],
                    'status': "online",
                    'currentValue': "0mm, 5km/h, 1013hPa",
                    'beehiveId': "693ad7c84739d5289a1e0834",
                    'hiveLocation': "external",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e11a",
                    'name': "DHT22 Temp/Humidity Sensor",
                    'dataCapture': ["temperature", "humidity"],
                    'status': "online",
                    'currentValue': "35.2°C, 55%",
                    'beehiveId': "693ad7c84739d5289a1e0835",
                    'hiveLocation': "external",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e11b",
                    'name': "Raspberry Pi Bee Counter",
                    'dataCapture': ["bee_count"],
                    'status': "offline",
                    'currentValue': 38000,
                    'beehiveId': "693ad7c84739d5289a1e0835",
                    'hiveLocation': "external",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e11c",
                    'name': "Arducam 8MP Camera Module",
                    'dataCapture': ["image"],
                    'status': "online",
                    'currentValue': "Active",
                    'beehiveId': "693ad7c84739d5289a1e0835",
                    'hiveLocation': "external",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e121",
                    'name': "Sensirion SHT85 Env Monitor",
                    'dataCapture': ["temperature", "humidity", "co2", "voc"],
                    'status': "online",
                    'currentValue': "35.1°C, 60%, 430ppm, 2.3kΩ",
                    'beehiveId': "693ad7c84739d5289a1e0836",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e122",
                    'name': "AI Vision Bee Counter Pro",
                    'dataCapture': ["bee_count"],
                    'status': "online",
                    'currentValue': 48000,
                    'beehiveId': "693ad7c84739d5289a1e0836",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e123",
                    'name': "Alphasense OPC-N3 Pollen Monitor",
                    'dataCapture': ["pollen_concentration"],
                    'status': "online",
                    'currentValue': "Medium",
                    'beehiveId': "693ad7c84739d5289a1e0836",
                    'hiveLocation': "external",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e12a",
                    'name': "AM2302 Temp/Humidity Sensor",
                    'dataCapture': ["temperature", "humidity"],
                    'status': "offline",
                    'currentValue': "36.5°C, 65%",
                    'beehiveId': "693ad7c84739d5289a1e0837",
                    'hiveLocation': "honey_super",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e12b",
                    'name': "Infrared Bee Counter v2",
                    'dataCapture': ["bee_count"],
                    'status': "offline",
                    'currentValue': 40000,
                    'beehiveId': "693ad7c84739d5289a1e0837",
                    'hiveLocation': "honey_super",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e12f",
                    'name': "SenseAir K30 CO2 Sensor",
                    'dataCapture': ["temperature", "humidity", "co2"],
                    'status': "online",
                    'currentValue': "34.2°C, 59%, 415ppm",
                    'beehiveId': "693ad7c84739d5289a1e0838",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e130",
                    'name': "TensorFlow Bee Counter",
                    'dataCapture': ["bee_count"],
                    'status': "online",
                    'currentValue': 52000,
                    'beehiveId': "693ad7c84739d5289a1e0838",
                    'hiveLocation': "brood",
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e131",
                    'name': "AS7341 Multi-Spectrum Analyzer",
                    'dataCapture': ["lux", "uv_index", "vibration"],
                    'status': "online",
                    'currentValue': "1100lux, UV3, 0.2mm/s",
                    'beehiveId': "693ad7c84739d5289a1e0838",
                    'hiveLocation': "external",
                    'systems': ["data_collection", "defense"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e139",
                    'name': "LoadCell HX711 Scale Sensor",
                    'dataCapture': ["activity", "image"],
                    'status': "online",
                    'currentValue': "Medium",
                    'beehiveId': None,
                    'hiveLocation': "external",
                    'systems': ["harvesting"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e13a",
                    'name': "Harvest Readiness Monitor Pro",
                    'dataCapture': ["activity"],
                    'status': "online",
                    'currentValue': "High",
                    'beehiveId': None,
                    'hiveLocation': "external",
                    'systems': ["harvesting"],
                    'created_at': datetime.now(timezone.utc)
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
            '/api/sensors',
            data=json.dumps([
                {
                    '_id': "693b4c90943e75b9d619e13b",
                    'name': "Si7021 Humidity Sensor",
                    'dataCapture': ["temperature", "humidity"],
                    'status': "online",
                    'currentValue': "25°C, 45%",
                    'beehiveId': None,
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
                },
                {
                    '_id': "693b4c90943e75b9d619e13c",
                    'name': "Backup Weather Station",
                    'dataCapture': ["rainfall", "wind_speed", "barometric_pressure", "uv_index"],
                    'status': "offline",
                    'currentValue': "N/A",
                    'beehiveId': None,
                    'systems': ["data_collection"],
                    'created_at': datetime.now(timezone.utc)
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
