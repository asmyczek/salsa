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

ALERT_LOAD_SHEDDING_START = 'LOAD_SHEDDING_START'
ALERT_LOAD_SHEDDING_END = 'LOAD_SHEDDING_END'
ALERT_POWER_OUTAGE_START = 'POWER_OUTAGE_START'
ALERT_ROWER_OUTAGE_END = 'POWER_OUTAGE_END'
ALERT_POWER_OUTAGE_5MIN = 'POWER_OUTAGE_IN_5MIN'
ALERT_ROWER_OUTAGE_10MIN = 'POWER_OUTAGE_IN_10MIN'
ALERT_ROWER_OUTAGE_15MIN = 'POWER_OUTAGE_IN_15MIN'
ALERT_ROWER_OUTAGE_30MIN = 'POWER_OUTAGE_IN_30MIN'


def future_event(event_time):
    diff = event_time.replace(second=0, microsecond=0) - \
            datetime.now().replace(second=0, microsecond=0).astimezone(tz=None)
    return diff.total_seconds()


def alert_event(mqtt_client, config):
    def builder_function(alert, time):
        def event_function():
            logging.info(f'Publishing /alert {alert}')
            mqtt_client.publish(f'{config("mqtt", "topic")}/alert', alert, qos=2, retain=False)
        return time, event_function
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
        self._stage = 0

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
            self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/schedule', pub_schedule, qos=2, retain=False)
            for s in schedule['schedule']:
                start = s['start']
                if start > now:
                    alert_builder = alert_event(self._mqtt_client, self._config)
                    self._schedule_event(alert_builder(ALERT_POWER_OUTAGE_START, start))
                    self._schedule_event(alert_builder(ALERT_POWER_OUTAGE_5MIN, start - timedelta(minutes=-5)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_10MIN, start - timedelta(minutes=-10)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_15MIN, start - timedelta(minutes=-15)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_30MIN, start - timedelta(minutes=-30)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_END, s['end']))

    def query_stage(self, republish: bool = False):
        logging.debug('Requesting load shedding stage.')
        if (new_stage := salsa.get_stage()) >= 0:
            logging.info(f'Publishing /stage {new_stage}')
            self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/stage', new_stage, qos=2, retain=False)
            if new_stage != self._stage or republish:
                alert = ALERT_LOAD_SHEDDING_START if new_stage > 0 else ALERT_LOAD_SHEDDING_END
                logging.info(f'Publishing /alert {alert}')
                self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/alert', alert, qos=2, retain=False)
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
                    # status ping
                    self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/status', 'online', qos=2, retain=False)
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
