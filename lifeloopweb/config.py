import os

from lifeloopweb import exception


class Config(object):
    # TODO There should be no defaults here. They should be definable by the
    #      modules that actually want them
    DEFAULTS = {"flask.templates.folder": "templates",
                "email.templates.folder": "lifeloopweb/templates/email",
                "email.port": 1025,
                "production": False}

    def __init__(self):
        # TODO
        # * Walk os.environ and set well known key spaces
        # * Be able to have namespaced keys we can fetch
        #   i.e. flask.templates.path
        # * If we could set config overrides without losing the original start
        #   value, that would be awesome.
        # * If we could get a complete debug config map from the app easily at
        #   any time, that would also be delightful
        # * Also note env vars can't be dotted, but underscores
        #   could be stand-ins for dotted namespacing
        # * Lastly, certain keyspaces should probably be removed
        #   from the name: LIFELOOP_APP_PORT=5000 -> app.port=5000
        self._cfg = {}
        for key, default in self.DEFAULTS.items():
            env_key = self._to_env_key(key)
            if key in os.environ:
                default = os.environ[key]
            elif env_key in os.environ:
                default = os.environ[env_key]

            if key in self._cfg:
                raise exception.ConfigConflict(key=key, value=self._cfg[key])
            self._cfg.setdefault(key, default)

    def _to_env_key(self, key):
        return ('_'.join(key.split('.'))).upper()

    def get(self, key, default=None):
        if key not in self._cfg:
            env_key = self._to_env_key(key)
            if env_key not in os.environ:
                if default:
                    return default
                raise exception.ConfigKeyNotFound(key=key)
            else:
                # Lazily populate the config
                # TODO These should be enforced by the module explicitly.
                #      instead of deferring to the environment. Why? Because
                #      if we have a bad config we should fail early. What's
                #      that mean? We should also do validation
                self._cfg[key] = os.environ[env_key]
        return self._cfg[key]

    def get_array(self, key, default=None):
        return [value.strip() for value in self.get(key, default).split(",")]


CONF = Config()
