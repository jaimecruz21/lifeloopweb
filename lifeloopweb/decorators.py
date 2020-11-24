from functools import wraps
import flask

from lifeloopweb import logging
from lifeloopweb.db import models

LOG = logging.get_logger(__name__)


def can_search_users(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can_add_group:
                flask.flash("You are unauthorized to do this task.",
                            'danger')
                return flask.redirect(flask.url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_add_group(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can_add_group:
                flask.flash("You are unauthorized to do this task.",
                            'danger')
                return flask.redirect(flask.url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_group_member(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            group_id = kwargs.get('group_id')
            g = models.Group.get(group_id)
            if not g:
                flask.flash('Group not found, please try again.', 'danger')
                return flask.redirect(flask.url_for('index'))

            if not current_user.is_group_member(group_id):
                flask.flash("You are unauthorized to do this task.",
                            'danger')
                return flask.redirect(flask.url_for(
                    'groups.show', group_id=group_id))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_edit_group(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            group_id = kwargs.get('group_id')
            g = models.Group.get(group_id)
            if not g:
                flask.flash('Group not found, please try again.', 'danger')
                return flask.redirect(flask.url_for('index'))

            if not current_user.can_edit_group(group_id):
                flask.flash("You are unauthorized to do this task.",
                            'danger')
                return flask.redirect(
                    flask.url_for('groups.show', group_id=group_id))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_change_group_members_role(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            group_id = kwargs.get('group_id')
            group = models.Group.get(group_id)
            if not group:
                flask.flash('Group not found, please try again.', 'danger')
                return flask.redirect(flask.url_for('index'))

            if not current_user.can_change_group_members_role(group):
                flask.flash(
                    "You are unauthorized to do this task.", 'danger')
                return flask.redirect(
                    flask.url_for('groups.edit', group_id=group_id))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_edit_group_api(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            group_id = kwargs.get('group_id')
            g = models.Group.get(group_id)
            if not g:
                return '', 404

            if not current_user.can_edit_group(group_id):
                return '', 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_edit_org(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org_id = kwargs.get('org_id')
            o = models.Organization.get(org_id)
            if not o or not o.is_active:
                flask.flash('Organization not found, please try again.',
                            'danger')
                return flask.redirect(flask.url_for('index'))

            if not current_user.can_edit_org(org_id):
                flask.flash("You are unauthorized to do this task.",
                            'danger')
                return flask.redirect(
                    flask.url_for('orgs.show', org_id=org_id))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_edit_org_api(current_user):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org_id = kwargs.get('org_id')
            o = models.Organization.get(org_id)
            if not o or not o.is_active:
                return '', 404

            if not current_user.can_edit_org(org_id):
                return '', 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
