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

To start salsa service with different config or port run:
```bash
python -m service -c <config file name> -p <port>
```

### Docker

Build and run docker with:
```bash
docker build -t salsa-service:latest -f Dockerfile --build-arg CONFIG=config.json .
docker run --name salsa-service -p 8080:8080 salsa-service
```
New version of openssl (>1.1.1) breaks ssl with old Eskom API.
Dockerfile replaces openssl.cnf file with the version in ./docker directory. Remove copy line
from ./Dockerfile if you use a different base image with old ssl version.

### Home Assistant

If you have Home Assistant setup and mqtt configured, salsa service will send load shedding and power outage alerts
to the following configured topics:

* Stage notifications
```
<config topic name>/stage <int>
```
starting with 0 = no load shedding stage, 1,2,3,....load shedding infinity... 

* Alert notifications
```
<config topic name>/alert <alert>
```
with \<alert\> = {'alert': key, 'counter': min }:
* LOAD_SHEDDING_ON - in load shedding stage
* LOAD_SHEDDING_OFF - no load shedding
* POWER_OUTAGE_ON - power is scheduled to be off
* POWER_OUTAGE_OFF - no power outage
* POWER_OUTAGE_NOW - immediate power outage expected
* POWER_OUTAGE_IN - power outage is scheduled in {x} minute: 30, 15, 10 and 5 minutes

* Power outage schedule
```
<config topic name>/schedule <json>
```
Today's load shedding schedule in JSON format.

To update load shedding status on boot, publish a /sync message using home assistant start automation:
```
automation:
  - alias: Hass start
    trigger:
      platform: homeassistant
      event: start
    action:
    - service: mqtt.publish
      data:
        topic: load-shedding/sync
```

For sensor configuration and example automations see ./homeassistant.

