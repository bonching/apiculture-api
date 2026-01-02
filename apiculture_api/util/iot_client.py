import logging
import socketio
import time
import random
from threading import Thread

from apiculture_api.util.config import IOT_WEBSOCKET_URL, IOT_CONNECTION_TIMEOUT, IOT_SIMULATE_MODE

logger = logging.getLogger('iot_client')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)


class IoTClient:
    """
    Client for communicating with the IoT devices via Socket.IO
    """

    def __init__(self, server_url=None, timeout=None, simulate=None):
        """
        Initialize IOT client

        Args:
            server_url (str, optional): URL of the IoT WebSocket. Defaults to IOT_WEBSOCKET_URL.
            timeout (int, optional): Timeout for WebSocket connection. Defaults to IOT_CONNECTION_TIMEOUT.
            simulate (bool, optional): Simulate IoT connection. Defaults to False.
        """
        self.server_url = server_url or IOT_WEBSOCKET_URL
        self.timeout = timeout or IOT_CONNECTION_TIMEOUT
        self.simulate = simulate if simulate is not None else IOT_SIMULATE_MODE
        self.sio = socketio.Client() if not self.simulate else None
        self.connected = False
        self.last_response = None
        self.response_callbacks = {}

    def register_response_callback(self, event_name, callback):
        """
        Register a callback function to be called when an event is received

        Args:
            event_name (str): Event name
            callback (function): Function to be called when an event is received
        """
        logger.info(f"Registering callback for event {event_name}")
        self.response_callbacks[event_name] = callback

    def unregister_response_callback(self, event_name):
        """
        Unregister a callback function to be called when an event is received

        Args:
            event_name (str): Event name
        """
        if event_name in self.response_callbacks:
            logger.info(f"Unregistering callback for event {event_name}")
            del self.response_callbacks[event_name]

    def connect(self):
        """
        Establish Socket.IO connection with IoT device (or simulate connection)

        Returns:
            bool: True if connection is successful, False otherwise
        """
        if self.simulate:
            logger.info(f"[SIMULATION MODE] Simulating connection to IoT device")
            self.connected = True
            return True

        try:
            if self.connected:
                logger.warning("IoT device is already connected")
                return True

            # Register event handlers before connecting
            self._register_event_handlers()

            logger.info(f"Connecting to IoT device at {self.server_url}")
            self.sio.connect(self.server_url, wait_timeout=self.timeout)
            self.connected = True
            logger.info(f"Successfully connected to IoT device at {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IoT device at {self.server_url}: {e}")
            return False

    def emit_event(self, event_name, data):
        """
        Emit an event to IoT device (or simulate emission)

        Args:
            event_name (str): Event name
            data (dict): Command to send to IoT device

        Returns:
            dict: Response from IoT device
        """
        try:
            if self.simulate:
                logger.info(f"[SIMULATION MODE] Emitting event {event_name} with data {data}")
                self._simulate_response(event_name, data)
                return {'success': True, 'event': event_name, 'data': data, 'simulated': True}

            if not self.connected:
                logger.warning("Socket.IO connection not established; attempting to reconnect...")
                if not self.connect():
                    return {'success': False, 'error': 'Failed to reconnect to IoT device'}

            logger.info(f"Emitting event {event_name} to IoT device at {self.server_url} with data {data}")
            self.sio.emit(event_name, data)
            return {'success': True, 'event': event_name, 'data': data}
        except Exception as e:
            logger.error(f"Failed to send command to IoT device: {e}")
            return {'success': False, 'error': str(e)}

    def _simulate_response(self, event_name, data):
        """
        Simulate IoT response to IoT device after a short delay

        Args:
            event_name (str): Event name
            data (dict): Command to send to IoT device
        """
        def delayed_response():
            # Simulate network delay (0.5 to 1.5 seconds)
            delay = random.uniform(0.5, 1.5)
            time.sleep(delay)

            # determine response event name
            response_event = f"{event_name.split(':')[0]}:response" if ':' in event_name else f"{event_name}:response"

            # simulate success response (98% success rate)
            success = random.random() < 0.98

            response_data = {
                'success': success,
                'event': response_event,
                'state': data.get('state'),
                'timestamp': time.time(),
                'simulated': True
            }

            if not success:
                response_data['error'] = 'Simulated device error'

            logger.info(f"[SIMULATION MODE] received simulated response on {event_name} : {response_data}")

            # update last response
            self.last_response = {'event': event_name, 'data': response_data}

            # execute callback if registered
            if response_event in self.response_callbacks:
                callback = self.response_callbacks[response_event]
                try:
                    callback(response_data)
                except Exception as e:
                    logger.error(f"Error executing callback for simulated event {response_event}: {e}")

        # run simulate in background thread
        thread = Thread(target=delayed_response, daemon=True)
        thread.start()


    def close(self):
        """
        Close Socket.IO connection with IoT device (or end simulation)
        """
        if self.simulate:
            logger.info(f"[SIMULATION MODE] Closing simulated connection with IoT device at {self.server_url}")
            self.connected = False
            return

        try:
            if self.connected and self.sio.connected:
                logger.info(f"Closing IoT device at {self.server_url}")
                self.sio.disconnect()
                self.connected = False
        except Exception as e:
            logger.error(f"Failed to close IoT device at {self.server_url}: {e}")

    def _register_event_handlers(self):
        """
        Register Socket.IO event handlers for responses from IoT device
        """
        @self.sio.on('connect')
        def on_connect():
            logger.debug(f"Connected to IoT device at {self.server_url}")

        @self.sio.on('disconnect')
        def on_disconnect():
            logger.debug(f"Disconnected from IoT device at {self.server_url}")
            self.connected = False

        @self.sio.on('*')
        def catch_all(event, data):
            """Generic catch all handler for all events"""
            logger.info(f"Received event: {event} with data: {data}")

            # Execute callback if registered for this event
            if event in self.response_callbacks:
                callback = self.response_callbacks[event]
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Caught exception while handling event: {event}: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()