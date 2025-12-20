from datetime import datetime

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
            self.generate_alert_message(data_type_name, 'high', value, unit)
        elif value < base_value - variance:
            self.generate_alert_message(data_type_name, 'low', value, unit)

    def generate_alert_message(self, data_type, quantifier, value, unit):
        ANOMALY_MESSAGE_TEMPLATE = {
            'temperature': {
                'high': {
                    'title': 'Temperature is too high',
                    'message': f'Temperature exceeds normal range {value}{unit}'
                },
                'low': {
                    'title': 'Temperature is too low',
                    'message': f'Temperature falls below normal range {value}{unit}'
                }
            }
        }

        if data_type not in ANOMALY_MESSAGE_TEMPLATE:
            return

        if quantifier not in ANOMALY_MESSAGE_TEMPLATE[data_type]:
            return

        alert = ANOMALY_MESSAGE_TEMPLATE[data_type][quantifier]
        alert['severity'] = 'warning'
        enqueue_sse(alert)
