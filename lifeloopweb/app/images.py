#!/usr/bin/env python
# pylint: disable=singleton-comparison, unexpected-keyword-arg, no-value-for-parameter

import flask
from flask_login import login_required

from lifeloopweb.app import utils as app_utils
from lifeloopweb import config, forms, logging
from lifeloopweb.crossdomain import crossdomain
from lifeloopweb.db import models
from lifeloopweb.cloudinary import CloudinaryHandler

CONF = config.CONF
LOG = logging.get_logger(__name__)

images = flask.Blueprint('images', __name__, template_folder="templates")
URL_PREFIX = "/images"
BLUEPRINT = images

app_utils.wrap_context(images)


@images.route('/<string:entity_type>/<uuid:entity_id>', methods=['POST'])
@login_required
def create(_ctxt, entity_type, entity_id):
    url = flask.request.form.get('url')
    public_id = flask.request.form.get('public_id')
    redirect_url = get_image_redirect_url(entity_type, entity_id)
    try:
        with models.transaction() as session:
            i = models.Image(
                image_url=url,
                public_id=public_id)
            session.add(i)
        with models.transaction() as session:
            if entity_type == 'user':
                ui = models.UserImage(
                    image_id=i.id,
                    user_id=entity_id)
                session.add(ui)
            elif entity_type == 'group':
                gi = models.GroupImage(
                    image_id=i.id,
                    group_id=entity_id)
                session.add(gi)
            elif entity_type == 'org':
                oi = models.OrganizationImage(
                    image_id=i.id,
                    organization_id=entity_id)
                session.add(oi)
        flask.flash("Image saved successfully", "success")
    except Exception:
        message = "Failed to save image, please try again later"
        LOG.exception(message)
        flask.flash(message, "danger")
    return flask.redirect(redirect_url)


@images.route('/<uuid:image_id>/<string:entity_type>', methods=['POST'])
@login_required
def delete(_ctxt, image_id, entity_type):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                if entity_type == 'user':
                    ui = models.UserImage.get_by_image_id(image_id)
                    session.delete(ui)
                elif entity_type == 'group':
                    gi = models.GroupImage.get_by_image_id(image_id)
                    session.delete(gi)
                elif entity_type == 'organization':
                    oi = models.OrganizationImage.get_by_image_id(image_id)
                    session.delete(oi)
                i = models.Image.get(image_id)
                session.delete(i)
            CloudinaryHandler().delete([i.public_id])
            flask.flash("Image deleted successfully", "success")
        except Exception:
            message = "Failed to delete image, please try again later"
            LOG.exception(message)
            flask.flash(message, "danger")
    return flask.redirect(flask.request.referrer)


@images.route('/signature', methods=['GET', 'OPTIONS'])
@crossdomain(origin="*")
@login_required
def signature(_ctxt):
    params_to_sign = {k: v[0] for k, v in
                      sorted(dict(flask.request.args).items())}
    try:
        sig = CloudinaryHandler().get_signature(params_to_sign)
        return sig
    except Exception:
        LOG.exception("Failed to get the image signature")
        return ('Error occurred, please try again later', 400)


def get_image_redirect_url(entity_type, entity_id):
    if entity_type == 'user':
        redirect_url = flask.url_for('users.show', user_id=entity_id)
    elif entity_type == 'group':
        redirect_url = flask.url_for('groups.edit', group_id=entity_id)
    elif entity_type == 'org':
        redirect_url = flask.url_for('orgs.edit', org_id=entity_id)
    return redirect_url
