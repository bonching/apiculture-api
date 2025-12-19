
TASK_RUNNER_RANDOM_DELAY_CEILING = 10
SENSOR_HEARTBEAT_FREQUENCY = 10
IDLE_TIME_TO_MARK_SENSOR_AS_OFFLINE = 40
DATA_COLLECTION_SIMULATION_FREQUENCY = 30

DATA_COLLECTION_METRICS = {
    'temperature': { 'base_value': 34.5, 'variance': 2, 'unit': '°C', 'anomaly_rate': 10 },
    'humidity': { 'base_value': 58, 'variance': 5, 'unit': '%', 'anomaly_rate': 1 },
    'co2': { 'base_value': 420, 'variance': 30, 'unit': 'ppm', 'anomaly_rate': 1 },
    'voc': { 'base_value': 2.1, 'variance': 0.3, 'unit': 'kΩ', 'anomaly_rate': 1 },
    'sound': { 'base_value': 68, 'variance': 5, 'unit': 'dB', 'anomaly_rate': 1 },
    'vibration': { 'base_value': 0.3, 'variance': 0.1, 'unit': 'mm/s', 'anomaly_rate': 1 },
    'bee_count': { 'base_value': 45000, 'variance': 2000, 'unit': '', 'anomaly_rate': 1 },
    'lux': { 'base_value': 1200, 'variance': 200, 'unit': 'lux', 'anomaly_rate': 1 },
    'uv_index': { 'base_value': 4, 'variance': 1, 'unit': '', 'anomaly_rate': 1 },
    'pheromone': { 'base_value': 85, 'variance': 10, 'unit': '', 'anomaly_rate': 1 },
    'odor_compounds': { 'base_value': None, 'variance': None, 'unit': '', 'anomaly_rate': 1 },
    'rainfall': { 'base_value': 0, 'variance': 0.5, 'unit': 'mm', 'anomaly_rate': 1 },
    'wind_speed': { 'base_value': 5, 'variance': 2, 'unit': 'km/h', 'anomaly_rate': 1 },
    'barometric_pressure': { 'base_value': 1013, 'variance': 5, 'unit': 'hPa', 'anomaly_rate': 1 },
    'pollen_concentration': { 'base_value': 65, 'variance': 15, 'unit': '', 'anomaly_rate': 1 },
    'activity': { 'base_value': None, 'variance': None, 'unit': '', 'anomaly_rate': 1 }
}