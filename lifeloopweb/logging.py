# pylint: disable=abstract-method
import logging
from logging.handlers import RotatingFileHandler

from lifeloopweb import config, exception

CONF = config.CONF

CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

LOG_FORMAT = ("[%(asctime)s] %(levelname)8s: "
              "pid:%(process)d [%(name)s:%(lineno)d] %(message)s ")

BASE_NAME = __name__.split('.')[0]


class LevelOnlyFilter(logging.Filter):
    def __init__(self, level):
        self._level = level
        super().__init__()

    def filter(self, record):
        return record.levelno == self._level


def verify_log_level(log_level_name, key):
    # TODO This validation will happen in tortilla later
    acceptable_levels = ["DEBUG", "WARNING", "INFO", "ERROR", "CRITICAL"]
    if log_level_name not in acceptable_levels:
        raise exception.InvalidConfigValue(key=key,
                                           value=CONF.get(key))


def file_log_handler():
    env = CONF.get("environment")
    path = CONF.get("log.file.path").format(env)
    file_handler = RotatingFileHandler(path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    return file_handler


def setup_logging():
    app_logger = logging.getLogger(BASE_NAME)
    app_handler = logging.StreamHandler()

    conf_log_level = CONF.get("loglevel")
    verify_log_level(conf_log_level, "loglevel")

    app_logger.setLevel(conf_log_level)
    app_formatter = logging.Formatter(LOG_FORMAT)
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)


def get_logger(name):
    return logging.getLogger(name)


setup_logging()
