#!/usr/bin/env python
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter,too-many-nested-blocks

import flask
from flask_login import current_user, login_required
import sqlalchemy as sa

from lifeloopweb import (config, decorators, email, filehandler, forms,
                         logging, meeting, signature, subscription,
                         disqus, exception as exc)
from lifeloopweb.app import utils as app_utils, users
from lifeloopweb.cloudinary import CloudinaryHandler
from lifeloopweb.db import models
from lifeloopweb.helpers.group_helper import GroupHelper

CONF = config.CONF
DOMAIN = CONF.get("site.domain")
LOG = logging.get_logger(__name__)
VIDEO_EXTENSIONS = CONF.get_array('allowed.video.extensions')
GOOGLE_API_KEY = CONF.get('google.api.key')
GOOGLE_API_CLIENT_ID = CONF.get('google.api.client.id')

groups = flask.Blueprint('groups', __name__, template_folder='templates')
URL_PREFIX = "/groups"
BLUEPRINT = groups

helper = GroupHelper()
app_utils.wrap_context(groups)


@groups.route('/<uuid:group_id>/organization', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def org_add(_ctxt, group_id):
    form = forms.GroupAddOrgForm(flask.request.form)
    other_orgs = helper.get_unaffiliated_orgs_for_group(group_id)
    form.orgs.choices = [(str(o.id), o.name) for o in other_orgs]
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                o = models.Organization.get(form.orgs.data)
                if not o:
                    flask.flash('Organization not found. Please '
                                'try again later.', 'danger')
                else:
                    org_owners = session.query(models.User).join(
                        models.OrganizationMember,
                        models.User.id ==
                        models.OrganizationMember.user_id).join(
                            models.Organization,
                            models.Organization.id ==
                            models.OrganizationMember.organization_id).join(
                                models.OrganizationRole,
                                models.OrganizationRole.id ==
                                models.OrganizationMember.role_id).filter(
                                    models.Organization.id ==
                                    form.orgs.data).filter(
                                        models.OrganizationRole.description ==
                                        'Owner').all()
                    if current_user.id in [o.id for o in org_owners]:
                        flask.flash("Group associated to organization"
                                    " successfully.", 'success')
                        og = models.OrganizationGroup(
                            organization_id=form.orgs.data,
                            group_id=group_id)
                        session.add(og)
                    else:
                        notification_type = (
                            models.NotificationType.get_by_description(
                                'Group Organization Add Request'))
                        for oo in org_owners:
                            notification = models.Notification(
                                user_to_id=oo.id,
                                user_from_id=current_user.id,
                                notification_type_id=notification_type.id,
                                group_id=group_id,
                                organization_id=o.id)
                            reminder = helper.send_notification(notification)
                        group = models.Group.get(group_id)
                        if group:
                            mail_to = ','.join([u.email for u in org_owners])
                            email_type = email.GroupOrganizationAddRequestEmail()
                            helper.send_email(email_type,
                                              current_user.email,
                                              mail_to,
                                              reminder,
                                              group=group,
                                              org=o)
                            flask.flash('Notification successfully sent to'
                                        ' organization owner(s)!', 'success')
                        else:
                            flask.flash('Group not found. Please try'
                                        ' again later.', 'danger')
        except Exception:
            LOG.exception("Failed to send group org add notification: %s",
                          group_id)
            flask.flash('There was an error sending notification to'
                        ' organization owner(s)!',
                        'danger')
    return flask.redirect(flask.url_for('.edit',
                                        group_id=group_id))


@groups.route('/<uuid:org_id>/new', methods=['GET', 'POST'])
@login_required
@decorators.can_add_group(current_user)
def new(_ctxt, org_id):
    org = models.Organization.get(org_id)

    if not current_user.can_add_group(org_id=org.id):
        flask.flash("You can't add group.", 'danger')
        return flask.redirect(
            flask.url_for('users.show', user_id=current_user.id))
    if not org.is_payed_up and not org.is_in_trial():
        return helper.need_leaders(org.id)

    form = forms.GroupNewForm(flask.request.form)
    form.privacy_settings.choices = forms.privacy_setting_choices()
    form.org.choices = helper.group_creation_org_choices(org_id)
    form.org.data = org_id

    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        elif not helper.unique_group_name(form.org.data, form.name.data):
            flask.flash(
                '{} is the name of another group in your organization.'
                ' Please try again.'.format(form.name.data), 'danger')
        else:
            try:
                return helper.creation_workflow(form, org)
            except Exception:
                LOG.exception(
                    "Group creation failed for user id '%s'", current_user.id)
    context = {}

    subscription_driver = subscription.ChargifyDriver(org_id)
    available = org.available_licenses or org.is_in_trial()
    if org.creator.id == current_user.id:
        context['prices'] = subscription_driver.get_component_prices()
    else:
        if not available:
            flask.flash(
                "Your organization {} has no available Group leaders."
                " Please contact {}".format(
                    org.name, org.creator.full_name_and_email), 'danger')
            return flask.redirect(
                flask.url_for('orgs.edit', org_id=org_id))
    context['available'] = available

    context = {
        'form': form,
        'org': org}

    return flask.render_template('group/create.html', **context)


@groups.route('/<uuid:group_id>')
def show(_ctxt, group_id):
    tf = forms.TextMessageForm()
    text_message_form = helper.text_message_form(group_id, tf)
    ef = forms.MassEmailForm()
    mass_email_form = helper.custom_email_form(group_id, ef)
    group = models.Group.get(group_id)
    if not group or group.archived_at:
        flask.flash('Group not found. Please try again.', 'danger')
        return flask.redirect(flask.url_for('index'))
    elif not group.parent_org.activated_at:
        flask.flash('This group does not exist, please try again or contact'
                    ' an organization administrator for that group', 'danger')
        return flask.redirect(flask.url_for('index'))
    wtforms = {
        'group_leaders_email': forms.GroupLeadersEmailForm(),
        'mass_email': mass_email_form,
        'add_member': forms.AddMemberForm(),
        'text_message': text_message_form,
        'group_add_document': forms.GroupAddDocumentForm(),
        'group_add_google_doc': forms.GroupAddGoogleDocForm(),
        'group_meeting': forms.GroupMeetingForm(),
        'confirm': forms.ConfirmForm()}

    cloudinary = dict(entity_type='group', entity_id=group.id,
                      **CloudinaryHandler.cloudinary_elements())
    google_api = {'key': GOOGLE_API_KEY,
                  'client_id': GOOGLE_API_CLIENT_ID}

    context = {
        'add_member_return_url': flask.url_for(".show", group_id=group_id),
        'cloudinary': cloudinary,
        'current_user': current_user,
        'entity_type': 'group',
        'google_api': google_api,
        'group': group,
        'invited_users': helper.get_invited_users(group_id),
        'meetings': helper.get_meetings(group_id),
        'members': helper.get_users(group_id),
        'video_extensions': tuple(VIDEO_EXTENSIONS),
        'wtforms': wtforms}

    if current_user.is_authenticated:
        context['disqus_config'] = disqus.conf(current_user, group_id)
    return flask.render_template('group/view.html', **context)


@groups.route("/register/<token>", methods=['GET', 'POST'])
def register_user_by_invite_create(_ctxt, token):
    form = forms.RegisterForm(flask.request.form)
    try:
        invite_mail = email.GroupInviteNewMemberEmail()
        content = invite_mail.decrypt_token(token)
        address = content.get('mail_to')
        if not address:
            raise signature.InvalidSignature()
        if address and users.is_existing_user(address):
            raise exc.UserAlreadyExists(email=address)
    except (signature.InvalidSignature, exc.MalformedToken):
        flask.flash("Error occurred. Please try link in email again or "
                    "ask person to resend invite.",
                    "danger")
        return flask.redirect(flask.url_for("index"))
    except exc.UserAlreadyExists:
        flask.flash("""A user is already registered for {}.
                    Please login instead.""".format(address), "danger")
        return flask.redirect(flask.url_for("login"))

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
                            '  Please try again later.',
                            'danger')
                return flask.redirect(flask.url_for("login"))
            flask.flash("You've successfully registered.", 'success')
            return flask.redirect(flask.url_for('login'))

    form.email.data = address
    form_url = flask.url_for(
        ".register_user_by_invite_create", token=token)
    context = {
        'form': form,
        'form_url': form_url,
        'minyears': CONF.get("user.minyears")
    }
    return flask.render_template(
        'register_after_email.html', **context)


@groups.route('/<uuid:group_id>/user/<uuid:user_id>/role', methods=['POST'])
@login_required
@decorators.can_change_group_members_role(current_user)
def update_user(_ctxt, group_id, user_id):
    group = models.Group.get(group_id)
    org = group.parent_org
    if current_user.is_group_admin(org_id=org.id):
        group_role_choices = helper.get_role_choices()
    elif current_user.role_for_group(group_id):
        priority = current_user.role_for_group(group_id).priority
        group_role_choices = helper.get_role_choices(priority)
    else:
        group_role_choices = helper.get_role_choices(0)
    form = forms.GroupUserRoleForm(flask.request.form)
    form.role.choices = group_role_choices
    redirect_url = flask.url_for('.edit', group_id=group_id)
    if not form.validate():
        app_utils.flash_errors(form)
        return flask.redirect(redirect_url)
    try:
        with models.transaction() as session:
            gm = helper.get_member(group_id, user_id)
            if str(gm.role_id) != str(form.role.data):
                role = models.GroupRole.get(form.role.data)
                if role.description == 'Group Leader':
                    group = models.Group.get(group_id)
                    org = group.parent_org
                    if current_user.can_add_group(org_id=org.id):
                        if not org.available_licenses and not org.is_in_trial():
                            flask.flash((
                                'Your Group {} has no available Group'
                                ' Leader Licenses. Please contact {}'
                            ).format(org.name,
                                     org.creator.full_name_and_email),
                                        'danger')
                            return flask.redirect(redirect_url)
                    else:
                        flask.flash(
                            'Only organization creator can set this role.',
                            'danger')
                        return flask.redirect(redirect_url)
                gm.role_id = form.role.data
                nt = session.query(
                    models.NotificationType).filter(
                        models.NotificationType.description ==
                        'Group Role Change').first()
                notification = models.Notification(
                    notification_type_id=nt.id,
                    user_from_id=current_user.id,
                    user_to_id=user_id,
                    group_id=group_id,
                    acknowledge_only=True)
                helper.send_notification(notification)
                flask.flash('Notification sent to member of role change',
                            'success')
            if gm.can_cohost_meeting != form.cohost_meeting.data:
                gm.can_cohost_meeting = form.cohost_meeting.data
            session.add(gm)
        flask.flash("User updated successfully", "success")
    except Exception:
        LOG.exception("Failed to change user %s in group %s to role %s",
                      user_id, group_id, form.role.data)
        flask.flash("There was an error changing the user's role.",
                    'danger')
    return flask.redirect(redirect_url)


@groups.route('/<uuid:group_id>/edit')
@login_required
@decorators.can_edit_group(current_user)
def edit(_ctxt, group_id):
    tf = forms.TextMessageForm()
    text_message_form = helper.text_message_form(group_id, tf)
    ef = forms.MassEmailForm()
    mass_email_form = helper.custom_email_form(group_id, ef)

    group = models.Group.get(group_id)
    if not group.parent_org.activated_at:
        flask.flash('This group does not exist, please try again or contact'
                    ' an organization administrator for that group', 'danger')
        return flask.redirect(flask.url_for('index'))
    other_orgs = helper.get_unaffiliated_orgs_for_group(group_id)
    members = helper.get_users(group_id)
    invited_users = helper.get_invited_users(group_id)
    wtforms = {
        'add_member': forms.AddMemberForm(),
        'group_add_org': forms.GroupAddOrgForm(),
        'confirm': forms.ConfirmForm(),
        'group_edit': forms.GroupEditForm(),
        'link': forms.LinkForm(),
        'mass_email': mass_email_form,
        'role_forms': {},
        'text_message': text_message_form,
        'tinymce_api_key': CONF.get('tinymce.api.key')}

    # TODO This is ripe for optimization. It's nice to get the models
    #      but we should eager load the meet_time_types at least to
    #      save N unexpected trips to the database
    wtforms['group_edit'].meet_times.data = [
        t.meet_time_type for t in group.meet_times]
    wtforms['group_edit'].privacy_settings.choices = forms.privacy_setting_choices()
    helper.populate_primary_form(wtforms['group_edit'], group)
    add_member_return_url = flask.url_for(".edit", group_id=group_id)
    wtforms['group_add_org'].orgs.choices = [('', 'Select Organization')] + [
        (str(o.id), o.name) for o in other_orgs]
    role_forms = {}
    org = group.parent_org

    if current_user.is_group_admin(org_id=org.id):
        group_role_choices = helper.get_role_choices()
    elif current_user.role_for_group(group_id):
        priority = current_user.role_for_group(group_id).priority
        group_role_choices = helper.get_role_choices(priority)
    else:
        group_role_choices = helper.get_role_choices(0)
    for user, group_member, role in members:
        group_user_role_form = forms.GroupUserRoleForm()
        group_user_role_form.role.choices = group_role_choices
        group_user_role_form.role.data = str(role.id)
        group_user_role_form.cohost_meeting.data = (
            group_member.can_cohost_meeting)
        role_forms[user.id] = group_user_role_form

    cloudinary = dict(entity_type='group', entity_id=group.id,
                      **CloudinaryHandler.cloudinary_elements())

    context = {
        'add_member_return_url': add_member_return_url,
        'cloudinary': cloudinary,
        'group': group,
        'invited_users': invited_users,
        'members': members,
        'role_forms': role_forms,
        'wtforms': wtforms}
    return flask.render_template('group/edit.html', **context)


@groups.route('/<uuid:group_id>/user', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def user_add(_ctxt, group_id):
    form = forms.AddMemberForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        group = models.Group.get(group_id)
        gr = models.GroupRole.get_by_description('Member')
        user = models.User.get_by_email(form.email.data)
        if not user:
            try:
                content = {'group': group, 'role': gr}
                mail = email.GroupInviteNewMemberEmail()
                mail.send(
                    current_user.email, form.email.data, **content)
                flask.flash("New member sent invite", "success")
            except Exception:
                LOG.exception("Error sending org invite email.")
                flask.flash(
                    "Error sending invite email, please try again later.",
                    "danger")
        else:
            gm = helper.get_member(group_id, user.id)
            if gm:
                flask.flash("User is already a member of the group. "
                            "User not invited.", "info")
                return flask.redirect(flask.url_for(
                    '.edit', group_id=group_id))
            try:
                helper.notify_join(user, group)
            except Exception:
                message = "Error occurred, please try again later"
                LOG.exception(message)
                flask.flash(message, 'danger')
    return flask.redirect(form.return_url.data)


@groups.route('/<uuid:group_id>/org/<uuid:org_id>/unaffiliate',
              methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def org_unaffiliate(_ctxt, group_id, org_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                og = session.query(models.OrganizationGroup).filter(
                    sa.and_(
                        models.OrganizationGroup.organization_id == org_id,
                        models.OrganizationGroup.group_id == group_id)).first()
                session.delete(og)
                flask.flash(
                    'Organization unaffiliated successfully!', 'success')
        except Exception:
            LOG.exception("Failed to unaffiliated org with id '%s' "
                          "for group %s", org_id, group_id)
            flask.flash('Failed to unaffiliated organization.', 'error')
    return flask.redirect(flask.url_for('.edit', group_id=group_id))


@groups.route('/<uuid:group_id>/meeting', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def meeting_create(_ctxt, group_id):
    form = forms.GroupMeetingForm(flask.request.form)
    group = models.Group.get(group_id)
    if not group:
        flask.flash('Group not found, please try again.', 'danger')
        return flask.redirect(flask.url_for('index'))
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                cohosts = session.query(models.GroupMember).filter(
                    models.GroupMember.group_id == group_id).filter(
                        models.GroupMember.can_cohost_meeting == 1).all()
            zoom = meeting.ZoomMeetingDriver()
            meeting_info = {
                'current_user': current_user,
                'cohosts': cohosts,
                'topic': form.topic.data,
                'type': form.meeting_type.data,
                'duration': form.duration.data,
                'start_time': form.start_datetime.data}
            result = zoom.schedule_meeting(**meeting_info)
            utc_meeting_start = helper.get_utc_date_time(
                current_user.timezone,
                form.start_datetime.data)
            with models.transaction() as session:
                m = models.ZoomMeeting(
                    meeting_id=result['id'],
                    duration=form.duration.data,
                    meeting_start=utc_meeting_start,
                    repeat_type=form.meeting_type.data,
                    topic=form.topic.data,
                    start_url=result['start_url'],
                    join_url=result['join_url'],
                    repeat_end_date=form.repeat_end_date.data,
                    user_id=current_user.id,
                    group_id=group_id)
                session.add(m)
            flask.flash("You successfully created your meeting! "
                        "Your meeting ID is {}".format(m.meeting_id),
                        'success')
        except Exception:
            message = "Failed to create meeting for group {}".format(
                group.name)
            LOG.exception(message)
            flask.flash(message, 'danger')
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/meeting/<uuid:meeting_id>', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def meeting_update(_ctxt, group_id, meeting_id):
    form = forms.GroupMeetingForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                m = models.ZoomMeeting.get(meeting_id)
                zoom = meeting.ZoomMeetingDriver()
                meeting_info = {
                    'meeting_id': m.meeting_id,
                    'current_user': current_user,
                    'topic': form.topic.data,
                    'duration': form.duration.data,
                    'type': form.meeting_type.data,
                    'start_time': form.start_datetime.data}
                zoom.update_meeting(**meeting_info)
                m = models.ZoomMeeting.get(meeting_id)
                utc_meeting_start = helper.get_utc_date_time(
                    current_user.timezone,
                    form.start_datetime.data)
                m.meeting_start = utc_meeting_start
                m.repeat_type = form.meeting_type.data
                m.repeat_end_date = form.repeat_end_date.data
                m.duration = form.duration.data
                m.topic = form.topic.data
                m.user_id = current_user.id
                m.group_id = group_id
                session.add(m)
            flask.flash("You successfully updated your meeting! "
                        "Your meeting ID is {}".format(m.meeting_id),
                        'success')
        except Exception:
            group = models.Group.get(group_id)
            message = "Failed to update meeting for group {}".format(
                group.name)
            LOG.exception(message)
            flask.flash(message, 'danger')
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route(
    '/<uuid:group_id>/meeting/<uuid:meeting_id>/delete', methods=['POST'])
@login_required
@decorators.can_edit_group_api(current_user)
def meeting_delete(_ctxt, group_id, meeting_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                m = models.ZoomMeeting.get(meeting_id)
                zoom = meeting.ZoomMeetingDriver()
                LOG.debug("Deleting meeting id: %s", id)
                meeting_info = {
                    'meeting_id': m.meeting_id,
                    'current_user': current_user}
                zoom.delete_meeting(**meeting_info)
                session.delete(m)
                flask.flash('Meeting deleted successfully!', 'success')
        except Exception:
            LOG.exception("Failed to delete meeting '%s' for group '%s'",
                          meeting_id, group_id)
            flask.flash('Failed to delete meeting.', 'error')
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/document', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def document_add(_ctxt, group_id):
    form = forms.GroupAddDocumentForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        googledoc = forms.GroupAddGoogleDocForm(flask.request.form)
        if googledoc.link.data:
            helper.google_doc_add(group_id, googledoc)
            return flask.redirect(flask.url_for('.show', group_id=group_id))
        helper.document_upload(group_id, form)
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/document/<uuid:document_id>', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def document_delete(_ctxt, group_id, document_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                d = models.GroupDocument.get(document_id)
                key = d.file_url.split('/')[-1]
                filehandler.S3FileHandler.delete(key)
                session.delete(d)
                flask.flash('Document deleted successfully!', 'success')
        except Exception:
            LOG.exception("Failed to delete document '%s' for group '%s'",
                          document_id, group_id)
            flask.flash('Failed to delete document.', 'error')
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/user/<uuid:user_id>', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def user_delete(_ctxt, group_id, user_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                gu = helper.get_member(group_id, user_id)
                session.delete(gu)
                flask.flash('Member removed successfully!', 'success')
        except Exception:
            LOG.exception("Failed to remove user '%s' from group '%s'",
                          user_id, group_id)
            flask.flash('Failed to remove member.', 'error')
    return flask.redirect(flask.url_for('.edit', group_id=group_id))


@groups.route('/<uuid:group_id>/group_text', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def group_text_create(_ctxt, group_id):
    form = forms.TextMessageForm(flask.request.form)
    message = form.message.data
    text = {}
    if form.recipient.data != "all":
        LOG.info("Sending text to %s", form.recipient.data)
        user = models.User.get(form.recipient.data)
        text[user.phone_number] = message
    else:
        group_users = helper.get_users(group_id, texting=True)
        for u in group_users:
            text[u.phone_number] = message
    helper.send_text_message(text)
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route(
    '/<uuid:group_id>/meeting/<uuid:meeting_id>/meeting_text',
    methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def meeting_text_create(_ctxt, group_id, meeting_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        group = models.Group.get(group_id)
        zoom_meeting = models.ZoomMeeting.get(meeting_id)
        group_leaders = helper.get_leaders(group_id, texting=True)
        group_users = helper.get_users(group_id, texting=True)

        # Three message sets due to hosts receiving two and leaders receiving
        # three separate messages
        join_messages = {}
        host_messages = {}
        leader_messages = {}

        for user in group_users:
            message = helper.meeting_join_text(user, group, zoom_meeting)
            join_messages[user.phone_number] = message
        for host in group_users:
            if zoom_meeting.can_host_meeting(host.id):
                message = helper.meeting_creator_alert_text(
                    host, group, zoom_meeting)
                host_messages[host.phone_number] = message
        for leader in group_leaders:
            if leader is not current_user:
                message = helper.leader_alert_text(
                    leader, current_user, group, zoom_meeting)
                leader_messages[leader.phone_number] = message

        # It is assumed that if the Join text is sent, necessary data for the
        # others are sent. Logs will be kept on all three, but flashes will
        # only occur for Join text
        helper.send_text_message(join_messages, flash=True)
        helper.send_text_message(host_messages, flash=False)
        helper.send_text_message(leader_messages, flash=False)

    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/join', methods=['POST'])
@login_required
def join_request(_ctxt, group_id):
    form = forms.ConfirmForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            group_leaders = helper.get_leaders(group_id, texting=True)
            if not group_leaders:
                flask.flash(
                    'There are not currently any group leaders for this group.'
                    ' No request sent. Please try again shortly.', 'danger')
            else:
                helper.join_request_handler(group_leaders, group_id)
        except Exception:
            LOG.exception(
                "Failed to send group join request to group %s", group_id)
            flask.flash(
                'There was an error sending your join request!', 'danger')
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/edit', methods=['POST'])
@login_required
@decorators.can_edit_group(current_user)
def update(_ctxt, group_id):
    form = forms.GroupEditForm(flask.request.form)
    form.privacy_settings.choices = forms.privacy_setting_choices()
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        try:
            with models.transaction() as session:
                update_group = models.Group.get(group_id)
                if update_group:
                    # TODO I wish form.populate_obj worked here, but it doesn't
                    update_group.description = form.description.data
                    update_group.member_limit = form.member_limit.data
                    update_group.privacy_setting_id = form.privacy_settings.data
                    update_group.anonymous = form.anonymous.data
                    update_group.age_range_id = (
                        form.age_range.data.id if form.age_range.data
                        else None)
                    update_group.gender_focus = form.gender_focus.data

                    group_meet_times = []
                    for m in form.meet_times.data:
                        group_meet_time = models.GroupMeetTime(
                            group_id=group_id,
                            meet_time_type_id=m.id)
                        group_meet_times.append(group_meet_time)

                    # NOTE: We can't just .clear(). It actually only sets
                    # the group_id column to NULL on each record for this user,
                    # then we issue N inserts after. Instead we can either
                    # 1) delete then insert
                    # 2) set math, delete if necessary, insert if necessary
                    # Considering there's no downside to deleting, and it's
                    # simpler, that's the approach below.
                    for mt in update_group.meet_times:
                        session.delete(mt)
                    update_group.meet_times.extend(group_meet_times)

                    update_group.group_type_id = (
                        form.group_category.data.id if
                        form.group_category.data else None)
                    session.add(update_group)
                    flask.flash('You successfully updated the group profile!',
                                'success')
                else:
                    flask.flash('No group found to update',
                                'danger')
                    return flask.redirect(
                        flask.url_for('.show', group_id=group_id))
        except Exception:
            LOG.exception("Failed to update group profile for group "
                          "%s", group_id)
            flask.flash('There was an error updating the group profile!',
                        'danger')
    return flask.redirect(flask.url_for('.edit', group_id=group_id))


@groups.route('/search', methods=['GET', 'POST'])
def search(_ctxt):
    form = forms.GroupSearchForm(flask.request.form)
    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        else:
            with models.transaction() as session:
                groups_query = session.query(models.Group).join(
                    models.GroupPrivacySetting,
                    models.Group.privacy_setting_id ==
                    models.GroupPrivacySetting.id).join(
                        models.OrganizationGroup,
                        models.OrganizationGroup.group_id ==
                        models.Group.id).join(
                            models.Organization,
                            models.Organization.id ==
                            models.OrganizationGroup.organization_id).join(
                                models.Address,
                                models.Address.id ==
                                models.Organization.address_id)
                # TODO Seeing a lot of this pattern. We should consider mapping
                #      forms -> models. Django serializers ish?
                form_pairs = {"name": models.Group.name,
                              "city": models.Address.city,
                              "state": models.Address.state,
                              "zip_code": models.Address.zip_code,
                              "group_category": models.GroupType.description,
                              "gender_focus": models.Group.gender_focus,
                              "age_range": models.AgeRange.description}
                for form_field, model_field in form_pairs.items():
                    form_data = getattr(form, form_field).data
                    if form_data:
                        groups_query = groups_query.filter(
                            model_field.like("{}%".format(form_data)))
                groups_query = groups_query.filter(
                    models.GroupPrivacySetting.description.like("Public%"))
                groups_query = groups_query.filter(
                    models.Group.archived_at.is_(None))
                all_groups = groups_query.order_by(models.Group.name).all()
                return flask.render_template(
                    'group/search.html', form=form, groups=all_groups)
    return flask.render_template('group/search.html', form=form)


@groups.route('/', methods=['GET'])
def index(_ctxt):
    prefix = flask.request.args.get('prefix')
    with models.transaction() as session:
        listed_groups = session.query(models.Group).join(
            models.GroupPrivacySetting,
            models.Group.privacy_setting_id ==
            models.GroupPrivacySetting.id).filter(
                sa.and_(models.GroupPrivacySetting.description.like('Public%'),
                        models.Group.name.like("{}%".format(prefix)),
                        models.Group.archived_at.is_(None))).order_by(
                            models.Group.name).all()
        formatted_groups = [{'id': str(g.id), 'name': g.name}
                            for g in listed_groups]
    return flask.jsonify(formatted_groups)


@groups.route('/<uuid:group_id>/groupmassemail', methods=['POST'])
def email_group(_ctxt, group_id):
    form = forms.MassEmailForm(flask.request.form)
    subject = form.subject.data
    message = form.message.data
    if form.recipient.data != "all":
        LOG.info("Sending email to %s", form.recipient.data)
        user = models.User.get(form.recipient.data)
        group_member_emails = user.email
    else:
        group_member_emails = ''
        group_users = helper.get_users(group_id, emails=True)
        for user, _, _ in group_users:
            group_member_emails += user.email + ', '
    if not group_member_emails:
        flask.flash('There was an error sending this email.')
    else:
        try:
            group = models.Group.get(group_id)
            mail_content = {
                'to': group_member_emails,
                'subject': subject,
                'message': message,
                'user': current_user,
                'group': group}
            group_mass_email = email.GroupMassEmail()
            group_mass_email.send(current_user.email,
                                  group_member_emails,
                                  **mail_content)
            flask.flash('You successfully sent your email message.',
                        'success')
        except Exception:
            LOG.exception("Error sending email to group")
            flask.flash('There was a problem sending your message.'
                        ' Sorry for the inconvenience.'
                        '  We will fix this as soon as we can.'
                        ' Please try again shortly.',
                        'danger')
    return flask.redirect(flask.url_for('.show', group_id=group_id))


@groups.route('/<uuid:group_id>/leadersemail', methods=['POST'])
def email_leaders(_ctxt, group_id):
    form = forms.GroupLeadersEmailForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        with models.transaction() as session:
            group_users = session.query(models.User).join(
                models.GroupMember,
                models.User.id == models.GroupMember.user_id).join(
                    models.Group,
                    models.Group.id == models.GroupMember.group_id).join(
                        models.GroupRole,
                        models.GroupRole.id ==
                        models.GroupMember.role_id).filter(
                            sa.and_(models.Group.id == group_id,
                                    models.GroupRole.description ==
                                    'Group Leader')).all()
            subject = form.subject.data
            # TODO: need to wrap this data in a cleaner (NEVER TRUST USER INPUT)
            message = form.message.data
            group_leader_emails = [u.email for u in group_users]
            group_leader_emails = ','.join(group_leader_emails)
            if not group_leader_emails:
                flask.flash('There are not currently any group leaders for'
                            ' this group.  No message sent'
                            ' Please try again shortly.',
                            'danger')
            else:
                try:
                    group = models.Group.get(group_id)
                    mail_content = {
                        'to': group_leader_emails,
                        'subject': subject,
                        'message': message,
                        'user': current_user,
                        'group': group}
                    group_leaders_email = email.GroupLeadersEmail()
                    group_leaders_email.send(current_user.email,
                                             group_leader_emails,
                                             **mail_content)
                    flask.flash('You successfully sent your email message.',
                                'success')
                except Exception:
                    LOG.exception("Error sending email to group leaders")
                    flask.flash('There was a problem sending your message.'
                                ' Sorry for the inconvenience.'
                                '  We will fix this as soon as we can.'
                                ' Please try again shortly.',
                                'danger')
    return flask.redirect(flask.url_for('.show', group_id=group_id))
