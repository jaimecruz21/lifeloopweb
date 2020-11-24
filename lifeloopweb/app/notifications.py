#!/usr/bin/env python
# pylint: disable=singleton-comparison, unexpected-keyword-arg, no-value-for-parameter

import datetime
from enum import Enum

import flask
from flask_login import current_user, login_required

import sqlalchemy as sa

from lifeloopweb.app import utils as app_utils
from lifeloopweb import config, email, forms, logging
from lifeloopweb.db import models


CONF = config.CONF
LOG = logging.get_logger(__name__)

notifications = flask.Blueprint('notifications', __name__,
                                template_folder="templates")
URL_PREFIX = "/notifications"
BLUEPRINT = notifications

app_utils.wrap_context(notifications)


class NotificationType(Enum):
    INVITATION_TO_JOIN_GROUP = 1
    GROUP_JOIN_REQUEST = 2
    INVITATION_TO_JOIN_ORGANIZATION = 3
    ORGANIZATION_JOIN_REQUEST = 4
    ORGANIZATION_ROLE_CHANGE = 5
    GROUP_ROLE_CHANGE = 6
    ORGANIZATION_CREATION_REQUEST = 7
    GROUP_ORGANIZATION_ADD_REQUEST = 8


notification_types = {
    NotificationType.INVITATION_TO_JOIN_GROUP: 'invitation to join group',
    NotificationType.GROUP_JOIN_REQUEST: 'group join request',
    NotificationType.INVITATION_TO_JOIN_ORGANIZATION:
        'invitation to join organization',
    NotificationType.ORGANIZATION_JOIN_REQUEST: 'organization join request',
    NotificationType.GROUP_ORGANIZATION_ADD_REQUEST: 'group organization add request',
    NotificationType.ORGANIZATION_ROLE_CHANGE: 'organization role change',
    NotificationType.GROUP_ROLE_CHANGE: 'group role change',
    NotificationType.ORGANIZATION_CREATION_REQUEST:
        'organization creation request'}


@notifications.route('/<uuid:notification_id>', methods=['GET'])
@login_required
def show(_ctxt, notification_id):
    """ Get notification info template by notification_id
    """
    n = models.Notification.get(notification_id)
    if n is None:
        return 'Notification not found', 404
    context = {'type': n.type.description}
    user_from = models.User.get(n.user_from_id)
    if user_from:
        context['user_from'] = user_from.to_dict()
    if n.organization_id:
        o = models.Organization.get(n.organization_id)
        context['org_name'] = o.name
        context['org_address'] = o.address.formatted
    if n.group_id:
        g = models.Group.get(n.group_id)
        context['group_name'] = g.name
        context['group_address'] = g.organizations[0].address.formatted
        context['parent_org_name'] = g.parent_org.name
    return flask.render_template('_partials/notification-info.html', **context)


def get_similar(notification):
    with models.transaction() as session:
        query = session.query(
            models.Notification).filter(
                sa.and_(
                    models.Notification.notification_type_id ==
                    notification.notification_type_id,
                    models.Notification.user_from_id ==
                    notification.user_from_id,
                    models.Notification.group_id ==
                    notification.group_id,
                    models.Notification.organization_id
                    == notification.organization_id))
        return query.all()


def accept_similar(notification):
    similar_notifications = get_similar(notification)
    for n in similar_notifications:
        n.accepted = datetime.datetime.utcnow()
        n.acknowledge = None
        n.save()


def decline_similar(notification):
    similar_notifications = get_similar(notification)
    for n in similar_notifications:
        n.declined = datetime.datetime.utcnow()
        n.acknowledge = None
        n.save()


def handle_response(notification):
    n = models.Notification()
    n.user_from_id = notification.user_to_id
    n.user_to_id = notification.user_from_id
    n.group_id = notification.group_id
    n.organization_id = notification.organization_id
    n.acknowledge_only = True
    if notification.accepted:
        n.notification_type_id = models.NotificationType.get_by_description(
            "Accepted Alert").id
        accept_similar(notification)
    elif notification.declined:
        n.notification_type_id = models.NotificationType.get_by_description(
            "Declined Alert").id
        decline_similar(notification)
    n.save()


@notifications.route('/<uuid:notification_id>/accept', methods=['GET'])
@login_required
def accept(_ctxt, notification_id):
    LOG.debug("Accept Notification")
    notification = models.Notification.get(notification_id)
    handle_accepted_notification(notification)
    handle_response(notification)
    send_acknowledged_request_email(notification)
    flask.flash(
        "Notification accepted successfully!", "success")
    return flask.redirect(
        flask.url_for('users.show', user_id=current_user.id))


@notifications.route('/<uuid:notification_id>/decline', methods=['GET'])
@login_required
def decline(_ctxt, notification_id):
    LOG.debug("Decline Notification")
    notification = models.Notification.get(notification_id)
    notification.declined = datetime.datetime.utcnow()
    notification.save()
    handle_response(notification)
    send_acknowledged_request_email(notification)
    flask.flash(
        "Notification declined successfully!", "success")
    return flask.redirect(
        flask.url_for('users.show', user_id=current_user.id))


@notifications.route('/<uuid:notification_id>/block', methods=['POST'])
@login_required
def block_as_spam(_ctxt, notification_id):
    form = forms.ConfirmForm(flask.request.form)
    if form.validate():
        LOG.debug("Block Notification as Spam")
        notification = models.Notification.get(notification_id)
        notification.declined = datetime.datetime.utcnow()
        notification.blocked_as_spam = True
        notification.save()
        flask.flash("Notification blocked successfully!", "success")
    else:
        flask.flash("Can't block notification as Spam. Please, try again"
                    " later", "danger")
    return flask.redirect(
        flask.url_for('users.show', user_id=current_user.id))


@notifications.route('/<uuid:notification_id>/acknowledge', methods=['GET'])
@login_required
def acknowledge(_ctxt, notification_id):
    LOG.debug("Acknowledge Notification")
    notification = models.Notification.get(notification_id)
    notification.acknowledged = datetime.datetime.utcnow()
    notification.save()
    flask.flash(
        "Notification acknowledgement handled successfully!", "success")
    return flask.redirect(
        flask.url_for('users.show', user_id=current_user.id))


def send_acknowledged_request_email(notification):
    mail_from = CONF.get("email.mailfrom")
    mail_to = notification.from_user.email
    r = email.RequestAcknowledgedEmail()
    r.send(mail_from, mail_to, notification=notification)


def handle_accepted_notification(notification):
    if notification.type.description.lower() == notification_types[
            NotificationType.GROUP_JOIN_REQUEST]:
        GroupJoinRequestNotificationAcceptHandler(notification).handle()
    if notification.type.description.lower() == notification_types[
            NotificationType.INVITATION_TO_JOIN_GROUP]:
        InvitationToJoinGroupNotificationAcceptHandler(notification).handle()
    if notification.type.description.lower() == notification_types[
            NotificationType.INVITATION_TO_JOIN_ORGANIZATION]:
        InvitationToJoinOrganizationNotificationAcceptHandler(
            notification).handle()
    if notification.type.description.lower() == notification_types[
            NotificationType.ORGANIZATION_JOIN_REQUEST]:
        OrganizationJoinRequestNotificationAcceptHandler(notification).handle()
    if notification.type.description.lower() == notification_types[
            NotificationType.ORGANIZATION_CREATION_REQUEST]:
        OrganizationCreationRequestNotificationAcceptHandler(
            notification).handle()
    if notification.type.description.lower() == notification_types[
            NotificationType.GROUP_ORGANIZATION_ADD_REQUEST]:
        GroupOrganizationAddRequestNotificationAcceptHandler(
            notification).handle()


class NotificationHandler:
    def __init__(self, notification):
        self.notification = notification
        self.notification.accepted = datetime.datetime.utcnow()
        self.notification.save()

    def handle(self):
        pass


class GroupJoinRequestNotificationAcceptHandler(NotificationHandler):
    def handle(self):
        LOG.debug("Handling accept group join request")
        with models.transaction() as session:
            gr = models.GroupRole.get_by_description('Member')
            gm = models.GroupMember(
                user_id=self.notification.user_from_id,
                group_id=self.notification.group_id,
                role_id=gr.id)
            session.add(gm)


class GroupOrganizationAddRequestNotificationAcceptHandler(NotificationHandler):
    def handle(self):
        LOG.debug("Handling accept group organization add request")
        with models.transaction() as session:
            og = models.OrganizationGroup(
                organization_id=self.notification.organization_id,
                group_id=self.notification.group_id)
            session.add(og)
            LOG.debug("Making org owner a member of the group")
            existing_gm = models.GroupMember.get_by_user_id(
                self.notification.user_to_id)
            if not existing_gm:
                gr = models.GroupRole.get_by_description('Member')
                gm = models.GroupMember(
                    user_id=self.notification.user_to_id,
                    group_id=self.notification.group_id,
                    role_id=gr.id)
                session.add(gm)


class GroupJoinRequestNotificationAcknowledgeHandler(NotificationHandler):
    def handle(self):
        LOG.debug("Handling acknowledge group join request")
        with models.transaction() as session:
            gr = models.GroupRole.get_by_description('Member')
            gm = models.GroupMember(
                user_id=self.notification.user_from_id,
                group_id=self.notification.group_id,
                role_id=gr.id)
            session.add(gm)


class InvitationToJoinGroupNotificationAcceptHandler(NotificationHandler):
    def handle(self):
        LOG.debug("Handling accept invitation to join group")
        with models.transaction() as session:
            gr = models.GroupRole.get_by_description('Member')
            gm = models.GroupMember(
                user_id=self.notification.user_to_id,
                group_id=self.notification.group_id,
                role_id=gr.id)
            session.add(gm)


class InvitationToJoinOrganizationNotificationAcceptHandler(
        NotificationHandler):
    def handle(self):
        LOG.debug("Handling accept invitation to join organization")
        with models.transaction() as session:
            org_role = models.OrganizationRole.get_by_description('Member')
            om = models.OrganizationMember(
                user_id=self.notification.user_to_id,
                organization_id=self.notification.organization_id,
                role_id=org_role.id)
            session.add(om)


class OrganizationJoinRequestNotificationAcceptHandler(NotificationHandler):
    def handle(self):
        LOG.debug("Handling accept organization join request")
        with models.transaction() as session:
            org_role = models.OrganizationRole.get_by_description('Member')
            om = models.OrganizationMember(
                user_id=self.notification.user_from_id,
                organization_id=self.notification.organization_id,
                role_id=org_role.id)
            session.add(om)


class OrganizationCreationRequestNotificationAcceptHandler(NotificationHandler):
    def handle(self):
        LOG.debug("Handling accept organization creation request")
        with models.transaction() as session:
            o = models.Organization.get(self.notification.organization_id)
            o.activated_at = datetime.datetime.utcnow()
            org_role = models.OrganizationRole.get_by_description('Owner')
            om = models.OrganizationMember(
                user_id=self.notification.user_from_id,
                organization_id=self.notification.organization_id,
                role_id=org_role.id)
            session.add(om)
