import functools
import itsdangerous
from lifeloopweb import exception as exc


class InvalidSignature(exc.LifeloopException):
    message = 'Could not validate the signature'


def get_signer(secret, salt, max_age=None):
    kls = itsdangerous.Signer
    kwargs = {'salt': salt}
    unsign_kwargs = {}
    if max_age is not None:
        kls = itsdangerous.TimestampSigner
        unsign_kwargs['max_age'] = max_age
    c = kls(secret, **kwargs)
    c.unsign = functools.partial(c.unsign, **unsign_kwargs)
    return c


def get_serializer(secret, salt, max_age=None):
    kls = itsdangerous.URLSafeSerializer
    loads_kwargs = {}
    kwargs = {'salt': salt}
    if max_age is not None:
        kls = itsdangerous.URLSafeTimedSerializer
        loads_kwargs['max_age'] = max_age
    c = kls(secret, **kwargs)
    c.loads = functools.partial(c.loads, **loads_kwargs)
    return c


def sign(value, secret, salt, max_age=None):
    signer = get_signer(secret, salt, max_age=max_age)
    return signer.sign(itsdangerous.want_bytes(value))


def unsign(value, secret, salt, max_age=None):
    signer = get_signer(secret, salt, max_age=max_age)
    try:
        return signer.unsign(value)
    except itsdangerous.SignatureExpired:
        raise InvalidSignature()
    except itsdangerous.BadTimeSignature:
        raise InvalidSignature()


def dumps(value, secret, salt, max_age=None):
    serializer = get_serializer(secret, salt, max_age=max_age)
    return serializer.dumps(value)


def loads(value, secret, salt, max_age=None):
    serializer = get_serializer(secret, salt, max_age=max_age)
    try:
        return serializer.loads(value)
    except itsdangerous.SignatureExpired:
        raise InvalidSignature()
    except itsdangerous.BadTimeSignature:
        raise InvalidSignature()
