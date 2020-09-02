# -*- coding: utf-8 -*-

from service.service import start_server
from service.mqtt import start_notifier, cleanup_notifier
from service.schedule_controller import start_schedule_controller
from service.utils import Config
import logging
import argparse


parser = argparse.ArgumentParser(description='Salsa Service')
parser.version = "Salsa Service v0.1"
parser.add_argument('-v', '--version',
                    action='version',
                    help='Print current service version.')
parser.add_argument('-c', '--config',
                    action='store',
                    type=str,
                    default='config.json',
                    help='Config file name')
parser.add_argument('-p', '--port',
                    action='store',
                    type=int,
                    default=8080,
                    help='HTTP service port')
args = parser.parse_args()


if __name__ == '__main__':
    config = Config(args.config)
    if args.port:
        config.set(args.port, 'server', 'port')
    logging.basicConfig(filename=config('logging', ' file'),
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.getLevelName(config('logging', 'level')))
    logging.info('Initialising Salsa service')
    mqtt_client = start_notifier(config)
    schedule_controller = start_schedule_controller(config, mqtt_client) if mqtt_client else None

    def terminate():
        logging.info('Service terminate called.')
        if schedule_controller:
            schedule_controller.stop()
        if mqtt_client:
            cleanup_notifier(mqtt_client)

    try:
        start_server(config, terminate)
    finally:
        logging.info('Salsa service server stopped')
