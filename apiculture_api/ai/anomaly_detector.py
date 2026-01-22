from apiculture_api.alerts_api import enqueue_sse
from apiculture_api.util.config import DATA_COLLECTION_METRICS

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

class AnomalyDetector:

    def __init__(self):
        pass

    def check_anomaly(self, metric):
        value = metric['value']
        data_type_id = metric['dataTypeId']

        data_type = mongo.data_types_collection.find_one({'_id': util.str_to_objectid(data_type_id)})
        unit = data_type['unit']
        data_type_name = data_type['data_type']

        base_value = DATA_COLLECTION_METRICS[data_type_name]['base_value']
        variance = DATA_COLLECTION_METRICS[data_type_name]['variance']
        if value > base_value + variance:
            self.generate_alert_message(data_type_name, 'high', value, unit, metric, data_type)
        elif value < base_value - variance:
            self.generate_alert_message(data_type_name, 'low', value, unit, metric, data_type)

    def generate_alert_message(self, data_type, quantifier, value, unit, metric, data_type_obj):
        # Get beehiveId from metric or from sensor
        beehive_id = metric.get('beehiveId')

        if not beehive_id and data_type_obj.get('sensor_id'):
            # Get beehiveId from sensor
            sensor = mongo.sensors_collection.find_one({'_id': util.str_to_objectid(data_type_obj['sensor_id'])})
            if sensor:
                beehive_id = sensor.get('beehiveId')

        # Get beehive name for better context in message
        beehive_name = None
        farm_name = None
        if beehive_id:
            hive = mongo.hives_collection.find_one({'_id': util.str_to_objectid(beehive_id)})
            if hive:
                beehive_name = hive.get('name', 'Unknown Beehive')
                if hive.get('farm_id'):
                    farm = mongo.farms_collection.find_one({'_id': util.str_to_objectid(hive['farm_id'])})
                    if farm:
                        farm_name = farm.get('name', 'Unknown Farm')

        location_context = ""
        if beehive_name:
            location_context = f"at {beehive_name}"
        if farm_name:
            location_context = f"in ({farm_name})"

        ANOMALY_MESSAGE_TEMPLATE = {
            'temperature': {
                'high': {
                    'title': 'Temperature Too High',
                    'message': f'Temperature exceeds normal range{location_context}: {value}{unit}'
                },
                'low': {
                    'title': 'Temperature Too Low',
                    'message': f'Temperature falls below normal range{location_context}: {value}{unit}'
                }
            },
            'humidity': {
                'high': {
                    'title': 'Humidity Too High',
                    'message': f'Humidity exceeds normal range{location_context}: {value}{unit}'
                },
                'low': {
                    'title': 'Humidity Too Low',
                    'message': f'Humidity falls below normal range{location_context}: {value}{unit}'
                }
            },
            'c02': {
                'high': {
                    'title': 'CO2 Level Too High',
                    'message': f'CO2 concentration exceeds normal range{location_context}: {value}{unit}'
                },
                'low': {
                    'title': 'CO2 Level Too Low',
                    'message': f'CO2 concentration falls below normal range{location_context}: {value}{unit}'
                }
            },
            'sound': {
                'high': {
                    'title': 'Sound Level Too High',
                    'message': f'Sound level exceeds normal range{location_context}: {value}{unit}'
                },
                'low': {
                    'title': 'Sound Level Too Low',
                    'message': f'Sound level falls below normal range{location_context}: {value}{unit}'
                }
            },
            'bee_count': {
                'high': {
                    'title': 'Bee Count Unusually High',
                    'message': f'Bee count exceeds normal range{location_context}: {value}{unit}'
                },
                'low': {
                    'title': 'Bee Count Unusually Low',
                    'message': f'Bee count falls below normal range{location_context}: {value}{unit}'
                }
            }
        }

        if data_type not in ANOMALY_MESSAGE_TEMPLATE:
            return

        if quantifier not in ANOMALY_MESSAGE_TEMPLATE[data_type]:
            return

        alert = ANOMALY_MESSAGE_TEMPLATE[data_type][quantifier].copy()
        alert['severity'] = 'warning'
        alert['alertType'] = 'anomaly_detected'
        alert['beehiveId'] = beehive_id
        alert['dataType'] = data_type
        alert['sensorValue'] = value

        # Add contextual information if available
        if beehive_name:
            alert['beehiveName'] = beehive_name
        if farm_name:
            alert['farmName'] = farm_name

        enqueue_sse(alert)
