# -*- coding: utf-8 -*-

import cherrypy
import logging
from typing import Dict
from pathlib import Path
from salsa import salsa
from json import JSONEncoder
from datetime import datetime


class App(object):

    @cherrypy.expose
    def index(self, **kwargs) -> str:
        return '<html><body>Salsa API service</body></html>'


@cherrypy.expose
class Api(object):

    @cherrypy.tools.json_out()
    def GET(self, **kwargs) -> Dict[str, object]:
        return {}


@cherrypy.expose
class ApiSuburbs(object):

    @cherrypy.tools.json_out()
    def GET(self, reload: bool = False) -> Dict[str, object]:
        return salsa.get_suburbs(reload)


@cherrypy.expose
class ApiFindSuburb(object):

    @cherrypy.tools.json_out()
    def GET(self, name: str) -> Dict[str, object]:
        return salsa.find_suburb(name)


@cherrypy.expose
class ApiSchedule(object):

    @cherrypy.tools.json_out()
    def GET(self, stage: int, name: str = None, block: str = None, days: int = 7) -> Dict[str, object]:
        schedule = salsa.get_schedule(stage, name=name, block=block, days=days)
        return {'stage': stage,
                'suburb': name,
                'block': block,
                'schedule': [{'start': s['start'].isoformat(), 'end': s['end'].isoformat()} for s in schedule]}


@cherrypy.expose
class ApiStatus(object):

    @cherrypy.tools.json_out()
    def GET(self, **kwargs) -> Dict[str, object]:
        return {'load_shedding_status': salsa.get_status()}


def start_server(config: Dict) -> None:
    app = App()
    app.api = Api()
    app.api.status = ApiStatus()
    app.api.suburbs = ApiSuburbs()
    app.api.findsuburb = ApiFindSuburb()
    app.api.schedule = ApiSchedule()

    api_config = {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'text/json')]
        }

    app_config = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': str(Path('.').resolve().absolute())
        },
        '/api': { **api_config }
    }

    logging.getLogger("cherrypy").propagate = False
    logging.getLogger("cherrypy.error").addHandler(logging.StreamHandler())

    global_config = {
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': '',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': config.server.port
    }
    cherrypy.config.update(global_config)
    cherrypy.quickstart(app, '/', app_config)
