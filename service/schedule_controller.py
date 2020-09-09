# -*- coding: utf-8 -*-

from threading import Thread, Event
from typing import Tuple
from datetime import datetime, timedelta
from salsa import salsa
from time import sleep
from json import dumps
from service.utils import PeekPriorityQueue
import paho.mqtt.client as mqtt
import logging


SLEEP_INTERVAL = 2  # in seconds
PULL_INTERVAL = 5   # in minutes

ALERT_LOAD_SHEDDING_ON = 'LOAD_SHEDDING_ON'
ALERT_LOAD_SHEDDING_OFF = 'LOAD_SHEDDING_OFF'
ALERT_POWER_OUTAGE_ON = 'POWER_OUTAGE_ON'
ALERT_ROWER_OUTAGE_OFF = 'POWER_OUTAGE_OFF'
ALERT_POWER_OUTAGE_IN = 'POWER_OUTAGE_IN'


def future_event(event_time):
    diff = event_time.replace(second=0, microsecond=0) - \
            datetime.now().replace(second=0, microsecond=0).astimezone(tz=None)
    return diff.total_seconds()


def alert_event(mqtt_client, config):
    def builder_function(time, alert, counter=None):
        start = time - timedelta(minutes=-counter) if counter else time

        def event_function():
            message = dumps({'alert': alert, 'counter': counter})
            logging.info(f'Publishing /alert {message}')
            mqtt_client.publish(f'{config("mqtt", "topic")}/alert', message, qos=2, retain=True)
        return start, event_function
    return builder_function


def on_syc(controller):
    def on_message(client, user_data, message):
        logging.info('Forcing status update.')
        controller.query_stage(republish=True)
    return on_message


class ScheduleController(Thread):

    def __init__(self, config, mqtt_client: mqtt.Client):
        Thread.__init__(self, name='Schedule controller')
        self._mqtt_client = mqtt_client
        self._mqtt_client.on_message = on_syc(self)
        self._config = config
        self._stopper = Event()
        self._event_queue = PeekPriorityQueue()
        self._stage = -1

    def stop(self):
        logging.debug('Requesting schedule controller stop.')
        if not self._stopper.is_set():
            self._stopper.set()
        self._clear_queue()
        self.join()

    def _schedule_event(self, event: Tuple):
        if future_event(event[0]) > 0:
            self._event_queue.put(event)
        else:
            logging.error(f'Scheduling event for past time {event[0]}')

    def _clear_queue(self):
        while not self._event_queue.empty():
            self._event_queue.get()

    def _set_stage(self, stage):
        self._stage = stage
        self._clear_queue()
        now = datetime.now().astimezone(tz=None)
        if stage > 0:
            logging.info('Creating alerts...')
            schedule = salsa.get_schedule(stage, block=self._config('salsa', 'block'), days=2)
            pub_schedule = dumps({'stage': stage,
                                  'block': schedule['block'],
                                  'schedule': [{'start': s['start'].isoformat(), 'end': s['end'].isoformat()}
                                               for s in schedule['schedule']]})
            logging.info(f'Publishing /schedule {pub_schedule}')
            self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/schedule', pub_schedule, qos=2, retain=True)
            for s in schedule['schedule']:
                start = s['start']
                if start > now:
                    alert_builder = alert_event(self._mqtt_client, self._config)
                    self._schedule_event(alert_builder(start, ALERT_POWER_OUTAGE_IN, counter=0))
                    self._schedule_event(alert_builder(start, ALERT_POWER_OUTAGE_IN, counter=5))
                    self._schedule_event(alert_builder(start, ALERT_POWER_OUTAGE_IN, counter=10))
                    self._schedule_event(alert_builder(start, ALERT_POWER_OUTAGE_IN, counter=15))
                    self._schedule_event(alert_builder(start, ALERT_POWER_OUTAGE_IN, counter=30))
                    self._schedule_event(alert_builder(s['end'], ALERT_ROWER_OUTAGE_OFF))
        elif stage == 0:
            pub_schedule = dumps({'stage': stage, 'schedule': []})
            logging.info(f'Publishing /schedule {pub_schedule}')
            self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/schedule', pub_schedule, qos=2, retain=True)

    def query_stage(self, republish: bool = False):
        logging.debug('Requesting load shedding stage.')
        if (new_stage := salsa.get_stage()) >= 0:
            logging.info(f'Publishing /stage {new_stage}')
            self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/stage', new_stage, qos=2, retain=True)
            if new_stage != self._stage or republish:
                message = dumps({'alert': ALERT_LOAD_SHEDDING_ON if new_stage > 0 else ALERT_LOAD_SHEDDING_OFF,
                                 'counter': None})
                logging.info(f'Publishing /alert {message}')
                self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/alert', message, qos=2, retain=True)
                self._set_stage(new_stage)
        else:
            logging.error(f'Load shedding query returned with error code {new_stage}')

    def run(self):
        logging.info('Starting scheduler controller.')
        interval = self._config('salsa', 'interval') or PULL_INTERVAL
        self.query_stage()
        while not self._stopper.is_set():
            now = datetime.now().astimezone(tz=None)
            if now.second < SLEEP_INTERVAL:

                # ping query status
                if (now.minute % interval) == 0:
                    self.query_stage()

                # remove previous dates
                while not self._event_queue.empty() and \
                        future_event(self._event_queue.peek()[0]) < 0:
                    event = self._event_queue.get()
                    logging.warning(f'Past event at {event[0]} identified. Discarding.')

                # process current event
                while not self._event_queue.empty() and \
                        future_event(self._event_queue.peek()[0]) == 0:
                    self._event_queue.get()[1]()

            sleep(SLEEP_INTERVAL)

        logging.info('Scheduler controller stopped.')


def start_schedule_controller(config, mqtt_client):
    schedule_controller = ScheduleController(config, mqtt_client)
    schedule_controller.start()
    return schedule_controller

