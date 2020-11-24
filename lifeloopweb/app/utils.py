#!/usr/bin/env python
# pylint: disable=singleton-comparison, unexpected-keyword-arg, no-value-for-parameter

import datetime
import functools

import flask

from lifeloopweb import context, lifeloopweb_app
from lifeloopweb.db import models


def _outer(route_obj):
    def _route(rule, **options):
        def _callable(f):
            endpoint = options.pop("endpoint", None)
            ctxt_func = functools.partial(f, context.Context())
            ctxt_func.__name__ = f.__name__
            route_obj.add_url_rule(rule, endpoint, ctxt_func, **options)
            return f
        return _callable
    return _route


def wrap_context(route_obj):
    route_obj.route = _outer(route_obj)


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            field_name = getattr(form, field).label.text
            message = "Error in the %s field - %s" % (field_name, error)
            flask.flash(message, "danger")


def create_user_from_form(form):
    session = models.Session
    hashed_password = lifeloopweb_app.bcrypt.generate_password_hash(
        form.password.data)
    user = models.User(
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        email=form.email.data,
        phone_number=form.phone_number.data,
        opt_in_texts=form.opt_in_texts.data,
        opt_in_emails=form.opt_in_emails.data,
        timezone=form.timezone.data,
        city=form.city.data,
        date_of_birth=datetime.date(
            form.year_of_birth.data,
            form.month_of_birth.data,
            form.day_of_birth.data),
        privacy_and_terms_agreed_at=datetime.datetime.utcnow(),
        verified_at=datetime.datetime.utcnow(),
        hashed_password=hashed_password)
    session.add(user)
    session.commit()
    return user
