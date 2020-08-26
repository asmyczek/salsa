## SALSA - South Africa Load Shedding API

Python API and tools for load shedding schedule, currently for Johannesburg and CityPower customers.
Feel free to extend it with other municipalities of provide API information.

### Install

Clone the repo, install pyenv and run:
```bash
pyenv virtualenv <python version, e.g. 3.8.5> salsa
pyenv activate salsa
pip install -r requirements.txt

python -m salsa -h
```

Example commands
```bash
# Get current load shedding stage
python -m salsa stage

# List all suburbs
python -m salsa list

# Find block id for suburb name
python -m salsa find -n <suburb name>

# Get schedule for stage and block id
python -m salsa schedule -s 2 -b 2A
```

For details see \_\_main\_\_.py.

### Service
Service provides a higher JSON API for testing.
To start, set HTTP port in config.json and run
```bash
python -m service
```

APIs:
```bash
../api/stage/
../api/list/
../api/find?name=<suburb name> or block=<block id>
../api/schedule?state=<1..8>&name=<suburb name> or block=<block id>&days=<results for today+days>
```
