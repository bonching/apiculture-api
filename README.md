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
python -m apiculture_api.simulator.data_collection_simulator --continuous --use-hardcoded-sensor
python -m apiculture_api.simulator.data_collection_simulator --bee-counter --data-type bee_count --sensor-id 693ae983cbd27112179d9552
python -m apiculture_api.simulator.harvest_simulator
python -m apiculture_api.simulator.defense_simulator --use-hardcoded-sensor
python -m apiculture_api.simulator.data_collection_simulator --backfill 24
```

```commandline
set PYTHONPATH=%CD%
python apiculture_api/simulator/data_collection_simulator.py
python apiculture_api/simulator/harvest_simulator.py
python apiculture_api/simulator/defense_simulator.py
```