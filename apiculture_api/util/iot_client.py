import json
import logging
from websocket import create_connection, WebSocketTimeoutException, WebSocketException

from apiculture_api.util.config import IOT_WEBSOCKET_URL, IOT_CONNECTION_TIMEOUT, IOT_SERVO_MOTOR_COMMAND

logger = logging.getLogger('iot_client')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)


class IoTClient:
    """
    Client for communicating with the IoT devices via WebSocket
    """

    def __init__(self, websocket_url=None, timeout=None):
        """
        Initialize IOT client

        Args:
            websocket_url (str, optional): URL of the IoT WebSocket. Defaults to IOT_WEBSOCKET_URL.
            timeout (int, optional): Timeout for WebSocket connection. Defaults to IOT_CONNECTION_TIMEOUT.
        """
        self.websocket_url = websocket_url or IOT_WEBSOCKET_URL
        self.timeout = timeout or IOT_CONNECTION_TIMEOUT
        self.ws = None

    def connect(self):
        """
        Establish WebSocket connection with IoT device

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            logger.info(f"Connecting to IoT device at {self.websocket_url}")
            self.ws = create_connection(self.websocket_url, timeout=self.timeout)
            logger.info(f"Successfully connected to IoT device at {self.websocket_url}")
            return True
        except WebSocketTimeoutException:
            logger.error(f"Failed to connect to IoT device at {self.websocket_url} within {self.timeout} seconds")
            return False
        except WebSocketException as e:
            logger.error(f"Failed to connect to IoT device at {self.websocket_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to IoT device at {self.websocket_url}: {e}")
            return False

    def send_command(self, command):
        """
        Send command to IoT device

        Args:
            command (dict): Command to send to IoT device

        Returns:
            dict: Response from IoT device
        """
        try:
            if not self.ws:
                logger.warning("WebSocket connection not established; attempting to reconnect...")
                if not self.connect():
                    return {'success': False, 'error': 'Failed to reconnect to IoT device'}

            # Convert command to JSON string
            command_json = json.dumps(command)
            logger.info(f"Sending command to IoT device: {command_json}")

            # Send command
            self.ws.send(command_json)

            # Wait for response
            response = self.ws.recv()
            logger.info(f"Received response from IoT device: {response}")

            # Parse response
            response_data = json.loads(response) if response else {'success': True}
            return response_data
        except WebSocketException:
            logger.error("Failed to send command to IoT device")
            return {'success': False, 'error': 'Failed to send command to IoT device'}
        except json.JSONDecodeError:
            logger.error("Failed to parse response from IoT device")
            return {'success': False, 'error': 'Failed to parse response from IoT device'}
        except Exception as e:
            logger.error(f"Failed to send command to IoT device: {e}")
            return {'success': False, 'error': str(e)}