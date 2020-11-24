#!/usr/bin/env python
# pylint:disable=unexpected-keyword-arg,no-value-for-parameter,too-many-nested-blocks

import flask
from flask_login import current_user, login_required

from lifeloopweb import config, forms, logging
from lifeloopweb.app import utils as app_utils
from lifeloopweb.db import models

CONF = config.CONF
LOG = logging.get_logger(__name__)

links = flask.Blueprint('links', __name__, template_folder='templates')
URL_PREFIX = "/link"
BLUEPRINT = links

app_utils.wrap_context(links)


def get_context(group_id, organization_id):
    if group_id:
        entity = 'group'
        entity_id = group_id
    else:
        entity = 'org'
        entity_id = organization_id
    values = {'%s_id' % entity: entity_id}
    return entity, entity_id, values


@links.route('/create/group/<uuid:group_id>',
             methods=['POST'], endpoint='create_for_group')
@links.route('/create/org/<uuid:organization_id>',
             methods=['POST'], endpoint='create_for_org')
@login_required
def create(_ctxt, group_id=None, organization_id=None):
    entity, entity_id, values = get_context(group_id, organization_id)

    form = forms.LinkForm(flask.request.form)
    can_edit_entity = getattr(current_user, 'can_edit_' + entity)
    if not can_edit_entity(entity_id) or not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                link = models.Link(
                    link_type_id=form.link_type.data.id,
                    url=form.link.data,
                    **(values if group_id else {'organization_id': entity_id}))
                session.add(link)
                flask.flash('You successfully added %s %s link!' %
                            ('a' if group_id else 'an', entity), 'success')
        except Exception:
            LOG.exception(
                "Failed to create link for %s '%s'", entity, entity_id)
            flask.flash(
                """There was an error adding the %s link.
                 Please try again later""" % entity,
                'danger')
    return flask.redirect(flask.url_for('%ss.edit' % entity, **values))


@links.route('/<uuid:link_id>/group/<uuid:group_id>/update',
             methods=['POST'], endpoint='update_for_group')
@links.route('/<uuid:link_id>/org/<uuid:organization_id>/update',
             methods=['POST'], endpoint='update_for_org')
@login_required
def update(_ctxt, link_id, group_id=None, organization_id=None):
    entity, entity_id, values = get_context(group_id, organization_id)

    form = forms.LinkForm(flask.request.form)
    can_edit_entity = getattr(current_user, 'can_edit_' + entity)
    if not can_edit_entity(entity_id) or not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                link = models.Link.get(link_id)
                link.link_type_id = form.link_type.data.id
                link.url = form.link.data
                session.add(link)
                flask.flash(
                    'You successfully updated the %s link!' % entity,
                    'success')
        except Exception:
            LOG.exception(
                "Failed to update link '%s' for %s '%s'",
                link_id, entity, group_id)
            flask.flash(
                """ There was an error updating the %s link. Please try again
                later """ % entity, 'danger')
    return flask.redirect(flask.url_for('%ss.edit' % entity, **values))


@links.route('/<uuid:link_id>/group/<uuid:group_id>/delete',
             methods=['POST'], endpoint='delete_for_group')
@links.route('/<uuid:link_id>/org/<uuid:organization_id>/delete',
             methods=['POST'], endpoint='delete_for_org')
@login_required
def delete(_ctxt, link_id, group_id=None, organization_id=None):
    entity, _, values = get_context(group_id, organization_id)

    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                link = models.Link.get(link_id)
                session.delete(link)
                flask.flash(
                    '%s link deleted successfully!' % entity.capitalize(),
                    'success')
        except Exception:
            LOG.exception(
                "Failed to delete link '%s' for %s '%s'",
                link_id, entity, group_id)
            flask.flash('Failed to delete %s link.' % entity, 'error')
    return flask.redirect(flask.url_for('%ss.edit' % entity, **values))
