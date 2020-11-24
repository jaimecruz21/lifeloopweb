import datetime

import flask
from flask_bcrypt import Bcrypt
from flask_login import current_user, login_required
import sqlalchemy as sa

from lifeloopweb import (config, decorators, email, forms, logging, signature)
from lifeloopweb.app import utils as app_utils
from lifeloopweb.cloudinary import CloudinaryHandler
from lifeloopweb.db import models
from lifeloopweb.helpers.base_helper import Helper

CONF = config.CONF
LOG = logging.get_logger(__name__)
VIDEO_EXTENSIONS = CONF.get_array('allowed.video.extensions')

users = flask.Blueprint('users', __name__, template_folder="templates")
URL_PREFIX = "/users"
BLUEPRINT = users

app_utils.wrap_context(users)
bcrypt = Bcrypt()
helper = Helper()

def existing_user(user_email):
    return models.User.get_by_email(user_email)


def is_existing_user(user_email):
    return existing_user(user_email) is not None


def get_orgs_groups(orgs_ids):
    # TODO: Refactor.
    # I think we should add Group.parent_org and Org.creator columns
    # to avoid these big db queries
    query = models.Session.query(models.Group).join(
        models.OrganizationGroup,
        models.Organization).filter(
            models.Organization.id.in_(orgs_ids),
            models.Group.archived_at.is_(None))
    return query.all()


@users.route('/<uuid:user_id>/passwordreset/validate/<token>',
             methods=['POST'])
def password_reset_validate(_ctxt, user_id, token):
    error_msg = "Error. Please start forgot password process over."
    try:
        forgot_email = email.ForgotPasswordEmail()
        content = forgot_email.decrypt_token(token)
        address = content.get('mail_to')
    except signature.InvalidSignature:
        flask.flash(error_msg, "danger")
        return flask.redirect(flask.url_for("forgot_password"))
    form = forms.PasswordResetForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        with models.transaction() as session:
            user = session.query(models.User).filter(
                sa.and_(models.User.id == user_id,
                        models.User.email == address)).first()
            if not user:
                flask.flash("Error changing password.", 'danger')
            else:
                try:
                    password = form.password.data
                    hashed_password = bcrypt.generate_password_hash(
                        password).decode('utf-8')
                    user.hashed_password = hashed_password
                    session.add(user)
                    flask.flash("Password reset successfully!", 'success')
                    return flask.redirect(flask.url_for('login'))
                except Exception:
                    LOG.exception("Password reset validation failed for user "
                                  "id '%s' and token '%s'", user_id, token)
                    flask.flash("Error changing password.", 'danger')
                    return flask.redirect(flask.url_for('forgot_password'))
    context = {
        'form': form,
        'user_id': user_id,
        'token': token}
    return flask.render_template('reset_password.html', **context)


@users.route('/<uuid:user_id>/profile', methods=['POST'])
@login_required
def profile(_ctxt, user_id):
    form = forms.UserProfileForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        user = existing_user(form.email.data)
        if user and current_user.email != form.email.data:
            flask.flash("That email address '{}' already exists,"
                        "  please try a different email address.".format(
                            form.email.data), 'danger')
        else:
            try:
                with models.transaction() as session:
                    user = models.User.get(current_user.id)
                    user.first_name = form.first_name.data
                    user.last_name = form.last_name.data
                    user.email = form.email.data
                    user.phone_number = form.phone_number.data
                    user.opt_in_texts = form.opt_in_texts.data
                    user.opt_in_emails = form.opt_in_emails.data
                    user.timezone = form.timezone.data
                    user.city = form.city.data
                    user.date_of_birth = datetime.date(
                        form.year_of_birth.data,
                        form.month_of_birth.data,
                        form.day_of_birth.data)
                    session.add(user)
                flask.flash('You successfully updated your profile!',
                            'success')
            except Exception:
                LOG.exception("Failed to save user profile for user "
                              "%s", user_id)
                flask.flash('There was an error updating your profile!',
                            'danger')
    context = {
        'user_id': user_id
    }
    return flask.redirect(flask.url_for('.show', **context))


@users.route('/<uuid:user_id>/group/<uuid:group_id>/delete', methods=['POST'])
@login_required
def group_leave(_ctxt, user_id, group_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        group_member = models.Session.query(models.GroupMember).filter(
            models.GroupMember.group_id == group_id).filter(
                models.GroupMember.user_id == user_id).first()
        group_leaders = models.Session.query(models.User).join(
            models.GroupMember,
            models.User.id == models.GroupMember.user_id).join(
                models.Group,
                models.Group.id == models.GroupMember.group_id).join(
                    models.GroupRole,
                    models.GroupRole.id == models.GroupMember.role_id).filter(
                        models.Group.id == group_id).filter(
                            models.GroupRole.description == 'Group Leader').all()
        if (group_member and group_leaders and
                len(group_leaders) == 1 and group_leaders[0].id == user_id):
            flask.flash('Unable to leave group when you are the last'
                        ' group leader.', 'danger')
        elif group_member:
            with models.transaction() as session:
                session.delete(group_member)
                session.commit()
            flask.flash('You left group successfully!', 'success')
        else:
            flask.flash('Error leaving group.', 'danger')
    return flask.redirect(flask.url_for('.show', user_id=user_id))


@users.route('/<uuid:user_id>')
@login_required
def show(_ctxt, user_id):
    if current_user.id != user_id and not current_user.super_admin:
        flask.flash('Permission denied.', 'danger')
        return flask.redirect('/')
    user = models.User.get(user_id)
    wtforms = {
        'confirm': forms.ConfirmForm(flask.request.form),
        'password_reset': forms.PasswordResetForm(flask.request.form),
        'user_profile': forms.UserProfileForm(flask.request.form, obj=user)}
    wtforms['user_profile'].timezone_default.data = user.timezone
    cloudinary = dict(entity_type='user', entity_id=user_id,
                      **CloudinaryHandler.cloudinary_elements())
    context = {
        'cloudinary': cloudinary,
        'user': user,
        'wtforms': wtforms}
    return flask.render_template('user/profile.html', **context)


@users.route('/', methods=['GET'])
@login_required
@decorators.can_search_users(current_user)
def index(_ctxt):
    prefix = flask.request.args.get('prefix')
    org_id = flask.request.args.get('org_id')
    with models.transaction() as session:
        query = session.query(models.User).filter(
            models.User.last_name.like('{}%'.format(prefix))
        ).order_by(models.User.last_name)
        if org_id:
            query = query.join(
                models.OrganizationMember,
                models.OrganizationMember.user_id == models.User.id
            ).join(
                models.Organization,
                models.Organization.id ==
                models.OrganizationMember.organization_id
            ).filter(models.Organization.id == org_id)
    users_formatted = [dict(id=str(user.id), name=user.full_name_and_email)
                       for user in query.all()]
    return flask.jsonify(users_formatted)
