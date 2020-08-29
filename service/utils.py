# -*- coding: utf-8 -*-

from typing import Dict, Any
from json import loads
from pathlib import Path
import logging


def load_config(config_file) -> Dict:
    try:
        config_file = Path(config_file).resolve()
        with config_file.open() as file:
            return loads(file.read())
    except FileNotFoundError:
        logging.error('Config file does not exist!')


class Config(object):
    _config: Dict = None

    def __init__(self, config_file: str = 'config.json'):
        self._config = load_config(config_file)

    def __call__(self, *args) -> Any:
        return self.get(*args)

    def get(self, *args) -> Any:
        c = self._config
        for a in args:
            if a in c:
                c = c[a]
            else:
                return None
        return c

    def set(self, value: Any, *args) -> Any:
        c = self._config
        for a in args[:-1]:
            if a not in c:
                c[a] = {}
            c = c[a]
        c[args[-1]] = value
