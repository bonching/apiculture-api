import logging
from pymongo import MongoClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mongo_client')
logger.setLevel(logging.INFO)

class ApicultureMongoClient():
    def __init__(self):
        try:
            self.client = MongoClient('mongodb://localhost:27017/')
            self.db = self.client['apiculture']  # Updated database name
            self.farms_collection = self.db['farms']
            self.hives_collection = self.db['hives']
            self.sensors_collection = self.db['sensors']
            self.metrics_collection = self.db['metrics']
            self.image_collection = self.db['images']

            self.client.server_info()
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            exit(1)


