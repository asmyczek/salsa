# -*- coding: utf-8 -*-

from threading import Thread, Event
from dataclasses import dataclass
from typing import Callable
from datetime import datetime, timedelta
from queue import PriorityQueue
from salsa import salsa
from time import sleep
import logging


SLEEP_INTERVAL = 2  # in seconds
PULL_INTERVAL = 5   # in minutes

LOAD_SHEDDING_STAGE = 'LOAD_SHEDDING_STAGE'
ALERT_LOAD_SHEDDING_START = 'LOAD_SHEDDING_START'
ALERT_LOAD_SHEDDING_END = 'LOAD_SHEDDING_END'
ALERT_POWER_OUTAGE_START = 'POWER_OUTAGE_START'
ALERT_ROWER_OUTAGE_END = 'POWER_OUTAGE_END'
ALERT_POWER_OUTAGE_5MIN = 'POWER_OUTAGE_IN_5MIN'
ALERT_ROWER_OUTAGE_10MIN = 'POWER_OUTAGE_IN_10MIN'
ALERT_ROWER_OUTAGE_15MIN = 'POWER_OUTAGE_IN_15MIN'
ALERT_ROWER_OUTAGE_30MIN = 'POWER_OUTAGE_IN_30MIN'


@dataclass(order=True)
class ScheduleEvent:
    key: datetime
    value: Callable

    def __init__(self, key, value):
        self.key = key
        self.value = value


def future_event(event_time):
    diff = event_time.replace(second=0, microsecond=0) - \
            datetime.now(tz=None).replace(second=0, microsecond=0)
    return diff and (1, -1)[diff < 0]


def alert_event(alert, time):
    def builder_function(mqtt_client, config):
        def event_function():
            logging.debug(f'Sending alert {alert}.')
            mqtt_client.publish(f'{config("mqtt", "topic")}/alert', alert, qos=2, retain=False)
        return ScheduleEvent(time, event_function)
    return builder_function


class ScheduleController(Thread):

    def __init__(self, config, mqtt_client):
        Thread.__init__(self, name='Schedule controller')
        self._mqtt_client = mqtt_client
        self._config = config
        self._stopper = Event()
        self._event_queue = PriorityQueue()
        self._stage = 0
        self._query_stage()

    def stop(self):
        if not self._stopper.is_set():
            self._stopper.set()
        self.join()
        self._clear_queue()
        logging.info('Schedule controller stopped.')

    def _schedule_event(self, event: ScheduleEvent):
        if future_event(event.key) > 0:
            self._event_queue.put(event)
        else:
            logging.error(f'Scheduling event for past time {event.key}')

    def _clear_queue(self):
        while not self._event_queue.empty():
            self._event_queue.empty()

    def _set_stage(self, stage):
        self._stage = stage
        self._clear_queue()
        now = datetime.now(tz=None)
        if stage > 0:
            logging.debug('Creating alerts...')
            for s in salsa.get_schedule(stage, block=self._config('salsa', 'block'), days=2)['schedule']:
                start = s['start']
                if start > now:
                    alert_builder = alert_event(self._mqtt_client, self._config)
                    self._schedule_event(alert_builder(ALERT_POWER_OUTAGE_START, start))
                    self._schedule_event(alert_builder(ALERT_POWER_OUTAGE_5MIN, start - timedelta(minutes=-5)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_10MIN, start - timedelta(minutes=-10)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_15MIN, start - timedelta(minutes=-15)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_30MIN, start - timedelta(minutes=-30)))
                    self._schedule_event(alert_builder(ALERT_ROWER_OUTAGE_END, s['end']))

    def _query_stage(self):
        logging.debug('Requesting load shedding stage.')
        if (new_stage := salsa.get_stage()) >= 0:
            self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/stage', new_stage, qos=2, retain=False)
            if new_stage != self._stage:
                logging.debug(f'Load shedding stage changed to {new_stage}.')
                self._mqtt_client.publish(f'{self._config("mqtt", "topic")}/alert',
                                          ALERT_LOAD_SHEDDING_START if new_stage > 0 else ALERT_LOAD_SHEDDING_END,
                                          qos=2,
                                          retain=False)
                self._set_stage(new_stage)
        else:
            logging.error(f'Load shedding query returned with error code {new_stage}')

    def run(self):
        logging.info('Starting scheduler controller.')
        interval = self._config('salsa', 'interval') or PULL_INTERVAL
        while not self._stopper.is_set():
            now = datetime.now(tz=None)
            if now.second < SLEEP_INTERVAL and (now.minute % interval) == 0:

                # ping query status
                self._query_stage()

                # remove previous dates
                while not self._event_queue.empty() and \
                        future_event(self._event_queue[0].key) < 0:
                    event = self._event_queue.get()
                    logging.warning(f'Past event at {event.key} identified. Discarding.')

                # process current event
                while not self._event_queue.empty() and \
                        future_event(self._event_queue[0].key) == 0:
                    self._event_queue.get().value()

            sleep(SLEEP_INTERVAL)
        logging.info('Scheduler controller stopped.')


def start_schedule_controller(config, mqtt_client):
    schedule_controller = ScheduleController(config, mqtt_client)
    schedule_controller.start()
    return schedule_controller
