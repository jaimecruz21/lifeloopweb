import base64
import hashlib
import hmac
import time
import flask

from lifeloopweb import config, logging

CONF = config.CONF
LOG = logging.get_logger(__name__)

DISQUS_SECRET_KEY = CONF.get('disqus.secret.key')
DISQUS_PUBLIC_KEY = CONF.get('disqus.public.key')
DISQUS_SITE_NAME = CONF.get('disqus.site.name')
DOMAIN = CONF.get('site.domain')
ENVIRONMENT = CONF.get('environment')


def format_str_url(endpoint, **kwargs):
    return '{}{}'.format(DOMAIN, flask.url_for(endpoint, **kwargs))


def conf(user, group_id):
    # create a JSON packet of our data attributes
    data = flask.json.dumps({
        'id': str(user.id),
        'username': user.full_name,
        'email': user.email
    })
    message = base64.b64encode(data.encode())
    timestamp = int(time.time())
    sig = hmac.HMAC(DISQUS_SECRET_KEY.encode(), '{} {}'.format(
        message.decode(), timestamp).encode(), hashlib.sha1).hexdigest()

    return {
        'page': {
            'remote_auth_s3': '{} {} {}'.format(message.decode(), sig, timestamp),
            'api_key': DISQUS_PUBLIC_KEY,
            'url': format_str_url('groups.show', group_id=group_id),
            'identifier': '{}-{}'.format(group_id, ENVIRONMENT)
        },
        'sso': {
            'name': DISQUS_SITE_NAME,
            'url': format_str_url('login', next=flask.request.path),
            'logout': format_str_url('logout')
        }
    }
