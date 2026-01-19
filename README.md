# Apiculture API

A Flask-based API for processing IoT sensor data and storing it in MongoDB.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```


2. Run tests:
```bash
python -m unittest discover tests
```


3. Run the application:
```bash
python -m apiculture_api.app
```

```commandline
set PYTHONPATH=%CD%
python apiculture_api/app.py
```


4. Run the simulators
```bash
python -m apiculture_api.simulator.data_collection_simulator
python -m apiculture_api.simulator.harvest_simulator
```

```commandline
set PYTHONPATH=%CD%
python apiculture_api/simulator/data_collection_simulator.py
python apiculture_api/simulator/harvest_simulator.py
```