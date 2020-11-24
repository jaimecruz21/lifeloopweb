from lifeloopweb import config, exception, logging, signature
from lifeloopweb.helpers.base_helper import Helper

CONF = config.CONF
LOG = logging.get_logger(__name__)

helper = Helper()

LATEST_VERSION = 1
SALT = 'lifeloop-default-salt'
EXPIRY = helper.days(int(CONF.get("token.expires.in.days")))
SECRET_KEY = CONF.get("signing.secret_key")


class TokenBase(object):
    def __init__(self):
        raise NotImplementedError("Cannot instantiate instances of TokenBase")

    def create(self, content, **kwargs):
        raise NotImplementedError("Cannot call create() on TokenBase")

    def get_content_from_payload(self, payload):
        raise NotImplementedError("Cannot call get_payload() on TokenBase")

    def _get_base(self, version):
        return {"version": version}


class TokenV1(TokenBase):
    VERSION = 1

    def __init__(self):
        # pylint: disable=super-init-not-called
        pass

    def get_content_from_payload(self, payload):
        if "content" not in payload:
            raise exception.MalformedTokenByMissingField(field="content")
        return payload["content"]

    def create(self, content, **kwargs):
        base_token = self._get_base(version=self.VERSION)
        base_token["content"] = content
        return base_token


def create(content, salt=None, expiry=None):
    token_impl = _get_token_impl(LATEST_VERSION)
    salt = salt or SALT
    expiry = expiry or EXPIRY
    token = token_impl.create(content, salt=salt, expiry=expiry)
    LOG.debug("Creating token with salt %s and expiry %s", salt, expiry)
    LOG.debug("Token contents %s", content)
    LOG.debug("Token: %s", token)
    return signature.dumps(token,
                           SECRET_KEY,
                           salt,
                           max_age=expiry)


def decrypt(token, salt=None, expiry=None):
    salt = salt or SALT
    expiry = expiry or EXPIRY
    try:
        output = signature.loads(token,
                                 SECRET_KEY,
                                 salt,
                                 max_age=expiry)
    except signature.InvalidSignature:
        raise exception.MalformedToken()
    LOG.debug("Decrypting token %s", token)
    LOG.debug("Decrypted Token Contents: %s", output)
    if "version" not in output:
        raise exception.MalformedToken(field="version")
    token_impl = _get_token_impl(output["version"])
    return token_impl.get_content_from_payload(output)


REGISTRY = {TokenV1.VERSION: TokenV1()}


def _get_token_impl(version):
    if version not in REGISTRY:
        raise exception.InvalidTokenVersion(version=version)
    return REGISTRY[version]
