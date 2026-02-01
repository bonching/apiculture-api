import json
import queue
import sys
from datetime import datetime, timezone

from bson import ObjectId

from apiculture_api.util.app_util import AppUtil
util = AppUtil()

from flask import jsonify, Blueprint, Response, request

alerts_api = Blueprint("alerts_api", __name__)

from apiculture_api.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setStream(open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('apiculture-api.log'),
        stream_handler
    ],
    encoding='utf-8'
)
logger = logging.getLogger('alerts_api')
logger.setLevel(logging.INFO)


sse_queue = queue.Queue()

# Track connected clients for reconnection
connected_clients = {}
client_counter = 0

def enqueue_sse(event_data):
    """'Callback' to enqueue a new event from tasks."""
    logger.info(f"Enqueuing new SSE event: {event_data}")

    event_data['read'] = False
    event_data['timestampMs'] = datetime.now(timezone.utc).timestamp()
    result = mongo.alerts_collection.insert_one(util.camel_to_snake_key(util.fix_datetime(util.remove_id_key(event_data))))
    logger.info(f"Successfully saved alert with IDs: {result.inserted_id}")
    event_data['id'] = util.objectid_to_str(result.inserted_id)

    # Convert all ObjectIds to strings to ensure JSON serializability
    event_data = util.objectid_to_str(event_data)

    sse_queue.put({"id": event_data['id'], "data": event_data})

def generate_alerts(last_event_id=None):
    """
    Event-driven SSE generator: Blocks on queue.get() for new events (reactive).
    Sends heartbeats on timeout to keep connection alive.
    Supports reconnection by sending missed events based on last_event_id.
    """
    # If reconnecting, send missed events first
    if last_event_id:
        logger.info(f"Client reconnecting with Last-Event-ID: {last_event_id}")
        try:
            # Find all alerts created after the last event ID
            last_alert = mongo.alerts_collection.find_one({"_id": ObjectId(last_event_id)})
            if last_alert:
                last_timestamp = last_alert.get('timestamp_ms')
                # Get all alerts created after this timestamp
                missed_alerts = list(mongo.alerts_collection.find({
                    "timestamp_ms": {"$gt": last_timestamp}
                }).sort("timestamp_ms", 1))

                if missed_alerts:
                    logger.info(f"Sending {len(missed_alerts)} missed events to reconnecting client")
                    for alert in missed_alerts:
                        alert_data = util.objectid_to_str(util.snake_to_camel_key(alert))
                        yield f"id: {alert_data['id']}\n"
                        yield f"data: {json.dumps(alert_data)}\n\n"
                else:
                    logger.info("No missed events to send")
            else:
                logger.warning(f"Last event ID not found in database: {last_event_id}")
        except Exception as e:
            logger.error(f"Error sending missed events: {str(e)}")

    # Now start streaming new events
    while True:
        try:
            # Block until event arrives (timeout=30s for heartbeats)
            event = sse_queue.get(timeout=30)
            logger.info(f"SSE event received: {event['data']}")
            # Send event with ID for reconnection tracking
            yield f"id: {event['id']}\n"
            yield f"data: {json.dumps(event['data'])}\n\n"
            sse_queue.task_done()  # Mark as processed (optional for cleanup)
        except queue.Empty:
            # No event; send heartbeat (comment format, no data)
            logger.debug("No events in queue; sending heartbeat")
            yield ": heartbeat\n\n"

@alerts_api.route('/sse/alerts')
def alerts_sse_stream():
    """
    Event-driven SSE endpoint: Streams events enqueued by background tasks.
    Supports automatic reconnection via Last-Event-ID header.
    """
    global client_counter
    client_counter += 1
    client_id = client_counter

    # Check if client is reconnecting (Last-Event-ID header)
    last_event_id = request.headers.get('Last-Event-ID')
    if not last_event_id:
        # Also check X-Last-Event-ID (some clients use this)
        last_event_id = request.headers.get('X-Last-Event-ID')

    logger.info(f"SSE connection established (client #{client_id})")
    if last_event_id:
        logger.info(f"Client #{client_id} reconnecting with Last-Event-ID: {last_event_id}")

    def stream_with_cleanup():
        """Wrapper generator to handle cleanup on disconnect"""
        try:
            # Send initial retry configuration (3 seconds)
            yield "retry: 3000\n\n"

            # Send a connection established event
            connection_event = {
                "alertType": "connection",
                "severity": "info",
                "message": "SSE connection established",
                "timestampMs": datetime.now(timezone.utc).timestamp()
            }
            yield f"event: connected\n"
            yield f"data: {json.dumps(connection_event)}\n\n"

            # Start streaming alerts
            for message in generate_alerts(last_event_id):
                yield message
        except GeneratorExit:
            logger.info(f"SSE client #{client_id} disconnected")
        except Exception as e:
            logger.error(f"SSE client #{client_id} error: {str(e)}")

    response = Response(
        stream_with_cleanup(),
        mimetype='text/event-stream'
    )
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Expose-Headers'] = 'Last-Event-ID'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable nginx buffering

    logger.info(f"SSE response configured for client #{client_id}")
    return response

@alerts_api.route('/api/alerts/<id>', methods=['PUT'])
def update_farm(id):
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.json
    if not data:
        logger.warning("No data provided in JSON body")
        return jsonify({'error': 'No data provided'}), 400

    try:
        alert = mongo.alerts_collection.find_one({"_id": ObjectId(id)})

        for key, value in data.items():
            alert[str(key)] = value
        alert['updated_at'] = datetime.now(timezone.utc)
        alert = util.remove_id_key(alert)

        logger.info(f"alert: {str(alert)}")

        mongo.alerts_collection.update_one({"_id": ObjectId(id)}, {'$set': util.camel_to_snake_key(alert)}, upsert=False)

        logger.info(f"Successfully updated alert with ID: {id}")
        return jsonify({'message': 'Alert updated successfully', 'data': str(id)}), 201
    except Exception as e:
        logger.error(f"Failed to update alert: {str(e)}")
        return jsonify({'error': f'Failed to update alert: {str(e)}'}), 500

@alerts_api.route('/api/alerts', methods=['POST'])
def create_alert():
    """
    POST endpoint to create a new alert and enqueue it to SSE stream.
    Accepts JSON event data in request body.
    """
    if not request.is_json:
        logger.warning("Request does not contain JSON data")
        return jsonify({'error': 'Request must be JSON'}), 400

    event_data = request.json
    if not event_data:
        logger.warning("No event data provided in JSON body")
        return jsonify({'error': 'No event data provided'}), 400

    try:
        logger.info(f"Received alert event via POST: {event_data}")

        # Enqueue the event to SSE (this will also save to database)
        enqueue_sse(event_data)

        # Return the alert ID
        return jsonify({
            'message': 'Alert created and enqueued successfully',
            'id': event_data.get('id')
        }), 201
    except Exception as e:
        logger.error(f"Failed to create alert: {str(e)}")
        return jsonify({'error': f'Failed to create alert: {str(e)}'}), 500

@alerts_api.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        alerts = util.snake_to_camel_key(util.objectid_to_str(list(mongo.alerts_collection.find().sort({'timestamp_ms': -1}).limit(30))))
        logger.info(f'data: {alerts}')
        return jsonify({'data': alerts}), 200
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        return jsonify({'error': f'Failed to get alerts: {str(e)}'}), 500