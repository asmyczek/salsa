# -*- coding: utf-8 -*-

from service.service import start_server
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
    else:
        logging.info('Loaded config.')
        logging.info(json.dumps(json.loads(config_str), indent=2, sort_keys=True))


def main():
    logging.info('Initialising Salsa service')
    config = load_config()

    try:
        start_server(config)
    finally:
        logging.info('Salsa service server stopped')


if __name__ == '__main__':
    main()
