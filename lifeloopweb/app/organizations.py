#!/usr/bin/env python
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
import datetime
import flask
from flask_login import current_user, login_required
from werkzeug.datastructures import MultiDict
import sqlalchemy as sa

from lifeloopweb import (decorators, email, forms, logging, sms, config,
                         signature, subscription, exception)
from lifeloopweb.app import utils as app_utils, users
from lifeloopweb.charts import Charts
from lifeloopweb.cloudinary import CloudinaryHandler
from lifeloopweb.db import models
from lifeloopweb.helpers.org_helper import OrgHelper

CONF = config.CONF
LOG = logging.get_logger(__name__)

orgs = flask.Blueprint('orgs', __name__, template_folder='templates')
URL_PREFIX = '/organizations'
BLUEPRINT = orgs

helper = OrgHelper()
app_utils.wrap_context(orgs)


@orgs.route('/')
def view_all(_ctxt):
    with models.transaction() as session:
        cls = models.Organization
        query = session.query(cls).filter(
            cls.activated_at.isnot(None)
        ).order_by(cls.name)
    context = dict(organizations=query.all(), contact_form=forms.ContactForm())
    return flask.render_template('organization/all.html', **context)


@orgs.route('/new')
@login_required
def new(_ctxt):
    form = helper.select_creation_form()
    return flask.render_template('organization/create.html', form=form)


@orgs.route('/create', methods=['POST'])
@login_required
def create(_ctxt):
    form = helper.select_creation_form()
    if not form.validate():
        app_utils.flash_errors(form)
        return flask.redirect(flask.url_for('.new'))
    return helper.creation_workflow(form)


@orgs.route('/<uuid:org_id>')
def show(_ctxt, org_id):
    org = models.Organization.get(org_id)
    if not org or org.activated_at is None:
        flask.flash('Organization not found. Please try again', 'danger')
        return flask.redirect(flask.url_for('index'))
    if org.vanity_name:
        return flask.redirect(org.vanity_name)
    return helper.show(org)


# TODO: URL hardcoded in organization-view-sort-groups.js
@orgs.route('/groups/sort', methods=['POST'])
@login_required
def groups_sort(_ctxt):
    payload = flask.request.form
    org_id = payload['org_id']

    if current_user.can_edit_org(org_id):
        group_ids = payload.getlist('group_ids[]')
        org = models.Organization.get_by_vanity_name(org_id)
        if org:
            org_id = org.id
        helper.groups_sort(org_id, group_ids)
        return '', 204
    return '', 403


@orgs.route('/<uuid:org_id>/join', methods=['POST'])
@login_required
def join_request(_ctxt, org_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        return flask.redirect(flask.redirect(
            flask.url_for('.show', org_id=org_id)))
    try:
        with models.transaction() as session:
            existing_om = helper.get_member(org_id, current_user.id)
            if existing_om:
                flask.flash('You are already a member of this organization',
                            'danger')
                return flask.redirect(flask.url_for('.show', org_id=org_id))
            org = models.Organization.get(org_id)
            if not org:
                flask.flash('No organization found', 'danger')
                return flask.redirect(flask.url_for('.show', org_id=org_id))
            org_admins_and_owners = helper.get_leaders(org_id)
            if not org_admins_and_owners:
                flask.flash(
                    'There is not currently any organization'
                    ' owners/administrators for this organization. No request'
                    ' sent Please try again shortly.', 'danger')
            else:
                notification_type = session.query(
                    models.NotificationType).filter(
                        models.NotificationType.description ==
                        'Organization Join Request').first()
                for user in org_admins_and_owners:
                    notification = models.Notification(
                        user_to_id=user.id,
                        user_from_id=current_user.id,
                        notification_type_id=notification_type.id,
                        organization_id=org_id)
                    reminder = helper.send_notification(notification)
                mail_to = ','.join([u.email for u
                                    in org_admins_and_owners])
                email_type = email.OrgJoinRequestEmail()
                helper.send_email(
                    email_type, current_user.email, mail_to, reminder, org=org)

                flask.flash('Request to join organization successfully sent!',
                            'success')
    except Exception:
        LOG.exception('Failed to send group join request to organization %s',
                      org_id)
        flask.flash('There was an error sending your join request!', 'danger')
    return flask.redirect(flask.url_for('.show', org_id=org_id))


@orgs.route('/<uuid:org_id>/chart', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def chart_filter(_ctxt, org_id):
    form = forms.ChartFilterForm(flask.request.form)
    if form.validate():
        org = models.Organization.get(org_id)
        duration = form.duration.data
        charts = Charts(org, duration)
        payload = charts.get(form.chart_id.data)
        code = 200
    else:
        payload = 'Bad Request'
        code = 400
    return flask.jsonify(payload), code


@orgs.route('/<uuid:org_id>/edit')
@login_required
@decorators.can_edit_org(current_user)
def edit(_ctxt, org_id):
    tf = forms.TextMessageForm()
    text_message_form = helper.text_message_form(org_id, tf)
    ef = forms.MassEmailForm()
    mass_email_form = helper.custom_email_form(org_id, ef)

    org = models.Organization.get(org_id)
    creator = org.creator
    members = helper.get_users(org_id)
    invited_users = helper.get_invited_users(org_id)

    wtforms = {
        'org': forms.OrgForm(),
        'mass_email': mass_email_form,
        'link': forms.LinkForm(),
        'chart_filter': forms.ChartFilterForm(),
        'confirm': forms.ConfirmForm(),
        'text_message': text_message_form,
        'add_member': forms.AddMemberForm(),
        'role_forms_dict': {}}

    helper.populate_primary_form(wtforms['org'], org)

    for member, role in members:
        role_form = forms.RoleForm()
        role_form.role.choices = helper.get_role_choices(org_id)
        role_form.role.data = role.id
        wtforms['role_forms_dict'][member.id] = role_form

    charts = Charts(org).get()
    cloudinary = dict(entity_id=org.id, entity_type='org',
                      **CloudinaryHandler.cloudinary_elements())

    context = {
        'add_member_return_url': flask.url_for(
            '.edit', org_id=org_id),
        'charts': charts,
        'cloudinary': cloudinary,
        'creator': creator,
        'current_user': current_user,
        'invited_users': invited_users,
        'members': members,
        'org': org,
        'wtforms': wtforms
        }
    return flask.render_template('organization/edit.html', **context)


@orgs.route('/<uuid:org_id>/group/<uuid:group_id>/archive', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def group_delete(_ctxt, org_id, group_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                group = models.Group.get(group_id)
                group.archived_at = datetime.datetime.utcnow(),
                session.add(group)
                flask.flash('Group archived successfully!', 'success')
        except Exception:
            LOG.exception("Failed to archive group with id '%s' "
                          "for org %s", group_id, org_id)
            flask.flash('Failed to archive group.', 'error')
    return flask.redirect(flask.url_for('.edit', org_id=org_id))


@orgs.route(
    '/<uuid:org_id>/group/<uuid:group_id>/unaffiliate', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def group_unaffiliate(_ctxt, org_id, group_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                og = session.query(models.OrganizationGroup).filter(sa.and_(
                    models.OrganizationGroup.organization_id == org_id,
                    models.OrganizationGroup.group_id == group_id
                )).first()
                session.delete(og)
                flask.flash('Group unaffiliated successfully!', 'success')
        except Exception:
            LOG.exception("Failed to unaffiliated group with id '%s' "
                          "for org %s", group_id, org_id)
            flask.flash('Failed to unaffiliated group.', 'error')
    return flask.redirect(flask.url_for('.edit', org_id=org_id))


@orgs.route("/register/<token>", methods=['GET', 'POST'])
def register_user_by_invite_create(_ctxt, token):
    form = forms.RegisterForm(flask.request.form)
    try:
        invite_mail = email.OrgInviteNewMemberEmail()
        content = invite_mail.decrypt_token(token)
        address = content.get('mail_to')
        if not address:
            raise signature.InvalidSignature()
        if address and users.is_existing_user(address):
            raise exception.UserAlreadyExists(email=address)
    except (signature.InvalidSignature, exception.MalformedToken):
        LOG.exception('Error decrypting token')
        flask.flash('Error occurred. Please try link in email again or'
                    ' ask person to resend invite.', 'danger')
        return flask.redirect(flask.url_for('index'))
    except exception.UserAlreadyExists:
        LOG.exception('User already exists')
        flask.flash('A user is already registered for {}.'
                    ' Please login instead.'.format(address), 'danger')
        return flask.redirect(flask.url_for('login'))

    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        else:
            try:
                user = app_utils.create_user_from_form(form)
                helper.handle_invite(content, user)
            except Exception:
                LOG.exception("Failed to register user with email '%s'",
                              form.email.data)
                models.Session.rollback()
                flask.flash('There was an error getting you registered.'
                            ' Please try again later.', 'danger')
                return flask.redirect(flask.url_for('login'))
            flask.flash("You've successfully registered.", 'success')
            return flask.redirect(flask.url_for('login'))

    form.email.data = address
    form_url = flask.url_for('.register_user_by_invite_create', token=token)
    context = {
        'form': form,
        'form_url': form_url,
        'minyears': CONF.get("user.minyears")
    }
    return flask.render_template(
        'register_after_email.html', **context)


@orgs.route('/<uuid:org_id>/user', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def user_add(_ctxt, org_id):
    form = forms.AddMemberForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        org = models.Organization.get(org_id)
        orgr = models.OrganizationRole.get_by_description('Member')
        user = models.User.get_by_email(form.email.data)
        if not user:
            try:
                content = {'org': org, 'role': orgr}
                mail = email.OrgInviteNewMemberEmail()
                mail.send(current_user.email, form.email.data, **content)
                flask.flash('New member sent invite', 'success')
            except Exception:
                LOG.exception('Error sending org invite email.')
                flask.flash(
                    'Error sending invite email, please try again later.',
                    'danger')
        else:
            om = helper.get_member(org_id, user.id)
            if om:
                flask.flash(
                    'User is already a member of the organization. User not'
                    ' added.', 'info')
                return flask.redirect(flask.url_for('.edit', org_id=org.id))
            try:
                helper.notify_join(user, org)
            except Exception:
                message = 'Error occurred, please try again later'
                LOG.exception(message)
                flask.flash(message, 'danger')
    return flask.redirect(form.return_url.data)


@orgs.route('/<uuid:org_id>/user/<uuid:user_id>/delete', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def user_delete(_ctxt, org_id, user_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                ou = helper.get_member(org_id, user_id)
                LOG.debug("Removing user '%s' from org '%s'", user_id, org_id)
                session.delete(ou)
                if form.confirm_checkbox.data:
                    org_groups = session.query(models.OrganizationGroup).filter(
                        models.OrganizationGroup.organization_id == org_id
                    ).all()
                    for og in org_groups:
                        gu = session.query(models.GroupMember).filter(
                            models.GroupMember.group_id == og.group_id).filter(
                                models.GroupMember.user_id == user_id).first()
                        if gu:
                            LOG.debug("Removing user '%s' from group '%s'",
                                      user_id, og.group_id)
                            session.delete(gu)
                flask.flash('Member removed successfully!', 'success')
        except Exception:
            LOG.exception("Failed to remove user '%s' from org '%s'",
                          user_id, org_id)
            flask.flash('Failed to remove member.', 'danger')
    return flask.redirect(flask.url_for('.edit', org_id=org_id))


@orgs.route('/<uuid:org_id>/user/<uuid:user_id>/role', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def user_role_update(_ctxt, org_id, user_id):
    form = forms.RoleForm(flask.request.form)
    form.role.choices = helper.get_role_choices(org_id)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            role = models.Session.query(
                models.OrganizationRole).get(form.role.data)

            if role.description == 'Group Creator':
                org = models.Session.query(models.Organization).get(org_id)
                if current_user != org.creator:
                    raise Exception

            with models.transaction() as session:
                om = helper.get_member(org_id, user_id)
                om.role_id = role.id
                session.add(om)
            nt = session.query(
                models.NotificationType
            ).filter(
                models.NotificationType.description ==
                'Organization Role Change'
            ).first()
            notification = models.Notification(
                notification_type_id=nt.id,
                user_from_id=current_user.id,
                user_to_id=user_id,
                organization_id=org_id,
                acknowledge_only=True)
            helper.send_notification(notification)
            flask.flash(
                "Updated user's role successfully. Notification sent to member"
                " of role change", 'success')
            return flask.redirect(flask.url_for('.edit', org_id=org_id))
        except Exception:
            LOG.exception('Failed to change user %s in org %s to role %s',
                          user_id, org_id, form.role.data)
            flask.flash(
                "There was an error changing the user's role.", 'danger')
    return flask.redirect(flask.url_for('.edit', org_id=org_id))


@orgs.route('/<uuid:org_id>/text', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def text_message_create(_ctxt, org_id):
    form = forms.TextMessageForm(flask.request.form)
    if form.recipient.data != "all":
        LOG.info("Sending text to %s", form.recipient.data)
        user = models.User.get(form.recipient.data)
        member_phone_numbers = [user.phone_number]
    else:
        org_users = helper.get_users(org_id, texting=True)
        member_phone_numbers = [u.phone_number for u in org_users]
    if not member_phone_numbers:
        flask.flash('There is not currently any org members that '
                    'are accepting text messages. No message sent '
                    'Please try again shortly.',
                    'danger')
    else:
        message = form.message.data
        for member_phone_number in member_phone_numbers:
            result = sms.sms_driver().send_text(
                member_phone_number, message)
        if result:
            flask.flash('You successfully sent your text message.',
                        'success')
        else:
            flask.flash('We could not send the text message(s). '
                        'Sorry for the inconvenience. '
                        'We will fix this as soon as we can. '
                        'Please try again shortly.',
                        'danger')
    return flask.redirect(flask.url_for('.edit', org_id=org_id))


@orgs.route('/search', methods=['GET', 'POST'])
def search(_ctxt):
    form = forms.OrgSearchForm(flask.request.form)
    context = dict(form=form)
    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        else:
            with models.transaction() as session:
                filters = [models.Organization.activated_at.isnot(None)]
                form_pairs = {"name": models.Organization.name,
                              "city": models.Address.city,
                              "state": models.Address.state,
                              "zip_code": models.Address.zip_code}
                for form_field, model_field in form_pairs.items():
                    form_data = form[form_field].data
                    if form_data:
                        filters.append(
                            model_field.like('{}%'.format(form_data)))
                query = session.query(models.Organization).join(
                    models.Address,
                    models.Address.id == models.Organization.address_id
                ).filter(*filters).order_by(models.Organization.name)
                context['orgs'] = query.all()
                return flask.render_template(
                    'organization/search.html', **context)
    return flask.render_template('organization/search.html', **context)


@orgs.route('/<uuid:org_id>', methods=['POST'])
@login_required
@decorators.can_edit_org(current_user)
def update(_ctxt, org_id):
    form = forms.OrgForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                org_to_update = models.Organization.get(org_id)
                helper.populate_org(org_to_update, form)
                session.add(org_to_update)
            flask.flash('You successfully updated the organization profile!',
                        'success')
        except Exception:
            LOG.exception('Failed to update org profile %s', org_id)
            flask.flash('There was an error updating the organization '
                        'profile!',
                        'danger')
    return flask.redirect(flask.url_for('.edit', org_id=org_id))


@orgs.route('/autocomplete', methods=['GET'])
def autocomplete(_ctxt):
    prefix = flask.request.args.get('prefix')
    with models.transaction() as session:
        query = session.query(models.Organization).filter(sa.and_(
            sa.or_(
                models.Organization.description.like('%{}%'.format(prefix)),
                models.Organization.name.like('%{}%'.format(prefix))
            ),
            models.Organization.activated_at.isnot(None)
        )).order_by(models.Organization.name)
        formatted_orgs = [
            dict(id=str(o.id), name=o.name) for o in query.all()]
    return flask.jsonify(formatted_orgs)


@orgs.route('/<uuid:org_id>/orgmassemail', methods=['POST'])
def email_org(_ctxt, org_id):
    form = forms.MassEmailForm(flask.request.form)
    subject = form.subject.data
    message = form.message.data
    if form.recipient.data != "all":
        LOG.info("Sending email to %s", form.recipient.data)
        user = models.User.get(form.recipient.data)
        org_member_emails = user.email
    else:
        org_member_emails = ''
        org_users = helper.get_users(org_id, emails=True)
        for user, _ in org_users:
            org_member_emails += user.email + ', '

    # TODO: need to wrap this data in a cleaner (NEVER TRUST USER INPUT)
    if not org_member_emails:
        flask.flash('There was an error sending this email.')
    else:
        try:
            org = models.Organization.get(org_id)
            mail_content = {
                'to': org_member_emails,
                'subject': subject,
                'message': message,
                'user': current_user,
                'org': org}
            org_mass_email = email.OrgMassEmail()
            org_mass_email.send(current_user.email,
                                org_member_emails,
                                **mail_content)
            LOG.info("Sending email to %s", org_member_emails)
            flask.flash('You successfully sent your email message.',
                        'success')
        except Exception:
            LOG.exception("Error sending email to group")
            flask.flash('There was a problem sending your message.'
                        ' Sorry for the inconvenience.'
                        '  We will fix this as soon as we can.'
                        ' Please try again shortly.',
                        'danger')
    return flask.redirect(flask.url_for('.show', org_id=org_id))


@orgs.route('/<uuid:org_id>/billing', methods=['GET', 'POST'])
@login_required
def billing(_ctxt, org_id):
    subscription_driver = subscription.ChargifyDriver(org_id)
    org = models.Organization.get(org_id)
    subscription_data = org.subscription_data
    credit_card = subscription_data.get('credit_card')
    card_info_form = forms.CardInfoForm(
        flask.request.form or MultiDict(mapping=credit_card))
    if flask.request.method == 'POST':
        if not card_info_form.validate():
            app_utils.flash_errors(card_info_form)
        else:
            if subscription_data:
                if org.cancel_at_end_of_period:
                    subscription_driver.stop_cancellation(org_id)
                result = subscription_driver.update_card_info(
                    org_id, card_info_form.data)
            else:
                result = subscription_driver.subscribe(current_user, org, card_info_form.data)
            if 'errors' in result:
                for error in result['errors']:
                    flask.flash(error, 'danger')
            else:
                message = "Your card information has been safely stored."
                flask.flash(message, 'success')
                return flask.redirect(flask.request.path)

    product_price = subscription_driver.get_product()['price_in_cents']
    if credit_card:
        card_info_form.full_number.data = credit_card['masked_card_number']

    context = {
        'user': current_user,
        'org': org,
        'wtforms': {
            'card_info': card_info_form,
            'license_update': forms.LicenseUpdateForm(
                quantity=org.purchased_licenses),
        },
        'prices': subscription_driver.get_component_prices(),
        'product_price': product_price,
        'quantity': org.group_leaders}
    return flask.render_template('organization/billing.html', **context)

@orgs.route('/<uuid:org_id>/billing/cancel')
@login_required
def billing_cancel(_ctxt, org_id):
    subscription_driver = subscription.ChargifyDriver(org_id)
    subscription_driver.cancel(org_id)
    message = "Organization scheduled to cancel on next billing date."
    flask.flash(message, 'success')
    return flask.redirect(flask.url_for('.billing', org_id=org_id))

@orgs.route('/<uuid:org_id>/billing/update', methods=['POST'])
@login_required
def billing_update(_ctxt, org_id):
    form = forms.LicenseUpdateForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        subscription_driver = subscription.ChargifyDriver(org_id)
        result = subscription_driver.update_license_quantity(
            org_id, form.quantity.data)
        if result:
            message = (
                "{} leader licenses now available to organizations"
                " you have created.").format(form.quantity.data)
            flask.flash(message, 'success')
        else:
            flask.flash("Please update your billing information first.", 'danger')
    return flask.redirect(flask.url_for('.billing', org_id=org_id))
