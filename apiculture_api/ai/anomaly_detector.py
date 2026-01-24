from apiculture_api.alerts_api import enqueue_sse
from apiculture_api.util.config import DATA_COLLECTION_METRICS

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
logger = logging.getLogger('anomaly_detector')
logger.setLevel(logging.INFO)

class AnomalyDetector:

    def __init__(self):
        pass

    def check_anomaly(self, metric):
        value = metric['value']
        data_type_id = metric['dataTypeId']

        logger.info(f"[ANOMALY CHECK] Starting anomaly check for metric: dtaTypeId={data_type_id}, value={value}")

        data_type = mongo.data_types_collection.find_one({'_id': util.str_to_objectid(data_type_id)})
        unit = data_type['unit']
        data_type_name = data_type['data_type']

        logger.info(f"[ANOMALY CHECK] Data type: {data_type_name}, unit={unit}")

        base_value = DATA_COLLECTION_METRICS[data_type_name]['base_value']
        variance = DATA_COLLECTION_METRICS[data_type_name]['variance']

        logger.info(f"[ANOMALY CHECK] {data_type_name}, base_value={base_value}, variance={variance}, range=[{base_value - variance}, {base_value + variance}]")

        if value > base_value + variance:
            self.generate_alert_message(data_type_name, 'high', value, unit, metric, data_type)
            logger.warning(f"[ANOMALY DETECTED] {data_type_name} HIGH: {value} > {base_value + variance}")
        elif value < base_value - variance:
            self.generate_alert_message(data_type_name, 'low', value, unit, metric, data_type)
            logger.warning(f"[ANOMALY DETECTED] {data_type_name} LOW: {value} > {base_value - variance}")
        else:
            logger.info(f"[ANOMALY CHECK] {data_type_name} value {value} is within normal range - NO ALERT")

    def generate_alert_message(self, data_type, quantifier, value, unit, metric, data_type_obj):
        logger.info(f"[ALERT GENERATION] Starting alert generation for {data_type} ({quantifier}): value={value}{unit}")
        logger.info(f"[ALERT GENERATION] Metric data: {metric}")

        # Get beehiveId from metric or from sensor
        beehive_id = metric.get('beehiveId')
        logger.info(f"[ALERT GENERATION] beehiveId from metric: {beehive_id}")

        if not beehive_id and data_type_obj.get('sensor_id'):
            # Get beehiveId from sensor
            logger.info(f"[ALERT GENERATION] No beehiveId in metric, checking sensor: {data_type_obj.get('sensor_id')}")
            sensor = mongo.sensors_collection.find_one({'_id': util.str_to_objectid(data_type_obj['sensor_id'])})
            if sensor:
                beehive_id = sensor.get('beehive_id')
                logger.info(f"[ALERT GENERATION] beehiveId from sensor: {beehive_id}")
            else:
                logger.warning(f"[ALERT GENERATION] Sensor not found for ID: {data_type_obj.get('sensor_id')}")

        # Get beehive name for better context in message
        beehive_name = None
        farm_name = None
        if beehive_id:
            logger.info(f"[ALERT GENERATION] Looking up beehive details for ID: {beehive_id}")
            hive = mongo.hives_collection.find_one({'_id': util.str_to_objectid(beehive_id)})
            if hive:
                beehive_name = hive.get('name', 'Unknown Beehive')
                logger.info(f"[ALERT GENERATION] Beehive name: {beehive_name}")
                if hive.get('farm_id'):
                    logger.info(f"[ALERT GENERATION] Looking up farm details for ID: {hive.get('farm_id')}")
                    farm = mongo.farms_collection.find_one({'_id': util.str_to_objectid(hive['farm_id'])})
                    if farm:
                        farm_name = farm.get('name', 'Unknown Farm')
                        logger.info(f"[ALERT GENERATION] Farm name: {farm_name}")
                    else:
                        logger.warning(f"[ALERT GENERATION] Farm not found for ID: {hive.get('farm_id')}")
            else:
                logger.warning(f"[ALERT GENERATION] Beehive not found for ID: {beehive_id}")

        location_context = ""
        if beehive_name:
            location_context = f" at {beehive_name}"
        if farm_name:
            location_context += f" ({farm_name})"

        logger.info(f"[ALERT GENERATION] Location context: {location_context}")

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
            'co2': {
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

        logger.info(f"[ALERT GENERATION] Checking if template exists for data_type: {data_type}")
        if data_type not in ANOMALY_MESSAGE_TEMPLATE:
            logger.warning(f"[ALERT GENERATION] No template found for data_type: {data_type} - SKIPPING ALERT")
            return

        logger.info(f"[ALERT GENERATION] Checking if template exists for quantifier: {quantifier}")
        if quantifier not in ANOMALY_MESSAGE_TEMPLATE[data_type]:
            logger.warning(f"[ALERT GENERATION] No template found for quantifier: {quantifier} in data_type: {data_type} - SKIPPING ALERT")
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

        logger.info(f"[ALERT GENERATION] Alert created: {alert}")
        logger.info(f"[ALERT GENERATION] Enqueueing SSE alert for {data_type} {quantifier} anomaly")

        enqueue_sse(alert)

        logger.info(f"[ALERT GENERATION] Alert enqueued successfully for {data_type} ({quantifier})")
