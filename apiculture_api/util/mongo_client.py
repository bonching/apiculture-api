import logging
import sys

from pymongo import MongoClient

from apiculture_api.util.config import MONGODB_URL

# Force stdout to UTF-8 on Windows (only if not already configured)
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        except (AttributeError, ValueError):
            pass # Already wrapped or not available
    if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding.lower() != 'utf-8':
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
        except (AttributeError, ValueError):
            pass # Already wrapped or not available

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../apiculture-api.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    encoding='utf-8'
)
logger = logging.getLogger('mongo_client')
logger.setLevel(logging.INFO)

class ApicultureMongoClient():
    def __init__(self):
        try:
            self.client = MongoClient(MONGODB_URL)
            self.db = self.client['apiculture']  # Updated database name
            self.farms_collection = self.db['farms']
            self.hives_collection = self.db['hives']
            self.sensors_collection = self.db['sensors']
            self.data_types_collection = self.db['data_types']
            self.metrics_collection = self.db['metrics']
            self.alerts_collection = self.db['alerts']
            self.image_collection = self.db['images']

            self.client.server_info()
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            exit(1)

    def close(self):
        """Close the MongoDB client connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures client is closed."""
        self.close()
        return False


