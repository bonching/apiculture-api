import json
import queue

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from flask import jsonify, Blueprint, Response

alerts_api = Blueprint("alerts_api", __name__)

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('apiculture-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('alerts_api')
logger.setLevel(logging.INFO)


sse_queue = queue.Queue()
def enqueue_sse(event_data):
    """'Callback' to enqueue a new event from tasks."""
    logger.info(f"Enqueuing new SSE event: {event_data}")
    sse_queue.put({"data": event_data})

def generate_alerts():
    """
    Event-driven SSE generator: Blocks on queue.get() for new events (reactive).
    Sends heartbeats on timeout to keep connection alive.
    """
    while True:
        try:
            # Block until event arrives (timeout=1s for heartbeats)
            event = sse_queue.get(timeout=5)
            logger.info(f"SSE event received: {event['data']}")
            yield f"data: {json.dumps(event['data'])}\n\n"
            sse_queue.task_done()  # Mark as processed (optional for cleanup)
        except queue.Empty:
            # No event; send heartbeat
            logger.info("No events in queue; sending heartbeat")
            yield ": heartbeat\n\n"

@alerts_api.route('/sse/alerts')
def alerts_sse_stream():
    """
    Event-driven SSE endpoint: Streams events enqueued by background tasks.
    """
    response = Response(
        generate_alerts(),
        mimetype='text/event-stream'
    )
    response.headers['Content-Type'] = 'text/event-stream'  # Explicit override
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    logger.info("SSE connection established - MIME: text/event-stream")  # Debug log
    return response

@alerts_api.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        alerts = util.snake_to_camel_key(util.objectid_to_str(list(mongo.alerts_collection.find())))
        logger.info(f'data: {alerts}')
        return jsonify({'data': alerts}), 200
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        return jsonify({'error': f'Failed to get alerts: {str(e)}'}), 500