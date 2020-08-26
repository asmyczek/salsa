# -*- coding: utf-8 -*-

from service.service import start_server
from service.mqtt import start_notifier, cleanup_notifier
from service.schedule_controller import ScheduleController
from pathlib import Path
from typing import Dict
from json import loads
from collections import namedtuple
import logging


def load_config() -> Dict:
    try:
        config_file = Path('config.json').resolve()
        with config_file.open() as file:
            config_str = file.read()
            return loads(config_str, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
    except FileNotFoundError:
        logging.error('Config file does not exist!')


if __name__ == '__main__':
    logging.info('Initialising Salsa service')
    config = load_config()
    mqtt_client = start_notifier(config)
    schedule_controller = None
    if mqtt_client:
        schedule_controller = ScheduleController(config, mqtt_client)
        schedule_controller.start()
    try:
        start_server(config)
    finally:
        if schedule_controller:
            schedule_controller.stop()
        if mqtt_client:
            cleanup_notifier(mqtt_client)
        logging.info('Salsa service server stopped')
