# pylint: disable=arguments-differ

from gunicorn.app import base
from gunicorn import config as gconfig

from lifeloopweb.lifeloopweb_app import app

BIND_HOST = "0.0.0.0"
BIND_PORT = 5000
WORKERS = 4
WORKER_CONNECTIONS = 100
WORKER_CLASS = "eventlet"
PROC_NAME = "lifeloopweb-server"
ACCESS_LOG = ""
ERROR_LOG = ""
LIMIT_LINE_REQUEST = 0
LOG_LEVEL = "debug"


class LifeLoopWebServer(base.Application):
    def init(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_config(self):
        self.cfg = gconfig.Config(self.usage, prog=self.prog)
        settings = {'bind': '%s:%s' % (BIND_HOST, BIND_PORT),
                    'workers': WORKERS,
                    'worker_connections': WORKER_CONNECTIONS,
                    'worker_class': WORKER_CLASS,
                    'proc_name': PROC_NAME,
                    'limit_request_line': LIMIT_LINE_REQUEST,
                    'loglevel': LOG_LEVEL,
                    'access_log_format': ' '.join(('%(h)s',
                                                   '%(l)s',
                                                   '%(u)s',
                                                   '%(t)s',
                                                   '"%(r)s"',
                                                   '%(s)s',
                                                   '%(b)s',
                                                   '"%(f)s"',
                                                   '"%(a)s"',
                                                   '%(T)s',
                                                   '%(D)s',))}

        for k, v in settings.items():
            self.cfg.set(k.lower(), v)

    def load(self):
        return app

    def run(self):
        base.Arbiter(self).run()


def run_server():
    lifeloopweb_server = LifeLoopWebServer()
    lifeloopweb_server.run()


if __name__ == '__main__':
    run_server()
