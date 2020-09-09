# -*- coding: utf-8 -*-

import cherrypy
import logging
from typing import Dict, Callable
from pathlib import Path
from salsa import salsa


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
class ApiList(object):

    @cherrypy.tools.json_out()
    def GET(self, reload: bool = False) -> Dict[str, object]:
        return salsa.get_suburbs(reload)


@cherrypy.expose
class ApiFind(object):

    @cherrypy.tools.json_out()
    def GET(self, name: str = None, block: str = None) -> Dict[str, object]:
        return salsa.find_suburb(name=name, block=block)


@cherrypy.expose
class ApiSchedule(object):

    @cherrypy.tools.json_out()
    def GET(self, stage: int, name: str = None, block: str = None, days: int = 7) -> Dict[str, object]:
        schedule = salsa.get_schedule(stage, name=name, block=block, days=days)
        return {'stage': stage,
                'suburb': name,
                'block': block,
                'schedule': [{'start': s['start'].isoformat(), 'end': s['end'].isoformat()}
                             for s in schedule['schedule']]}


@cherrypy.expose
class ApiStage(object):

    @cherrypy.tools.json_out()
    def GET(self, **kwargs) -> Dict[str, object]:
        return {'load_shedding_stage': salsa.get_stage()}


def start_server(config: Dict, terminate: Callable) -> None:
    app = App()
    app.api = Api()
    app.api.stage = ApiStage()
    app.api.list = ApiList()
    app.api.find = ApiFind()
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

    global_config = {
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': '',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': config('server', 'port')
    }

    cherrypy.log.error_log.propagate = False
    cherrypy.log.access_log.propagate = False
    cherrypy.engine.subscribe('stop', terminate)
    cherrypy.config.update(global_config)

    logging.info(f'Starting http server on port {config("server", "port")}.')
    cherrypy.quickstart(app, '/', app_config)
