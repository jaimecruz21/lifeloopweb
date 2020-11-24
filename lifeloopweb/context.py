#!/usr/bin/env python


class Context(object):
    """
    The Context class represents shared state across the request.
    While Flask provides App and Request context objects, this let's
    us abstract that behavior from Flask specifically, allowing us
    to be decoupled from any one given framework."""
    pass
