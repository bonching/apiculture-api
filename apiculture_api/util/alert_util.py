import time

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()


class AlertUtil:
    def __init__(self):
        pass

    def generate_dummy_alert(self):
        data = [
          {
            'severity': "critical",
            'title': "Sensor Non-Responsive",
            'message': "Bee Counter Gamma-1 has been offline for 2 hours",
            'beehiveName': "Gamma Hive",
            'farmName': "Ising Farm",
            'timestamp': "2 hours ago",
            'timestampMs': int(time.time()) - 2 * 60 * 60 * 1000
          },
          {
            'severity': "critical",
            'title': "Multiple Sensors Offline",
            'message': "All sensors in Epsilon Hive are non-responsive",
            'beehiveName': "Epsilon Hive",
            'farmName': "Alveare Farm",
            'timestamp': "3 hours ago",
            'timestampMs': int(time.time()) - 3 * 60 * 60 * 1000
          },
          {
            'severity': "warning",
            'title': "High Temperature Detected",
            'message': "Temperature exceeds normal range (35.2°C)",
            'beehiveName': "Gamma Hive",
            'farmName': "Ising Farm",
            'timestamp': "45 minutes ago",
            'timestampMs': int(time.time()) - 45 * 60 * 1000
          },
          {
            'severity': "warning",
            'title': "Elevated VOC Levels",
            'message': "Volatile organic compounds above threshold",
            'beehiveName': "Delta Hive",
            'farmName': "Alveare Farm",
            'timestamp': "1 hour ago",
            'timestampMs': int(time.time()) - 1 * 60 * 60 * 1000
          },
          {
            'severity': "info",
            'title': "Honey Production Milestone",
            'message': "Delta Hive reached 50kg production",
            'beehiveName': "Delta Hive",
            'farmName': "Alveare Farm",
            'timestamp': "30 minutes ago",
            'timestampMs': int(time.time()) - 30 * 60 * 1000
          },
          {
            'severity': "warning",
            'title': "Low Pheromone Activity",
            'message': "Pheromone concentration below optimal levels",
            'beehiveName': "Alpha Hive",
            'farmName': "Ising Farm",
            'timestamp': "15 minutes ago",
            'timestampMs': int(time.time()) - 15 * 60 * 1000
          },
          {
            'severity': "info",
            'title': "Weather Update",
            'message': "Incoming rainfall detected in 2 hours",
            'beehiveName': "Beta Hive",
            'farmName': "Ising Farm",
            'timestamp': "5 minutes ago",
            'timestampMs': int(time.time()) - 5 * 60 * 1000
          }
        ]
        mongo.alerts_collection.insert_many(util.camel_to_snake_key(util.fix_datetime(util.remove_id_key(data))))

if __name__ == '__main__':
    AlertUtil().generate_dummy_alert()
