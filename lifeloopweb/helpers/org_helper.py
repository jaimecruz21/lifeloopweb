#!/usr/bin/env python
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter,unused-argument
import datetime
import flask
from flask_login import current_user
import sqlalchemy as sa

from lifeloopweb import config, email, forms, logging
from lifeloopweb.cloudinary import CloudinaryHandler
from lifeloopweb.helpers.base_helper import Helper
from lifeloopweb.db import models

CONF = config.CONF
LOG = logging.get_logger(__name__)
VIDEO_EXTENSIONS = CONF.get_array('allowed.video.extensions')


class OrgHelper(Helper):
    # Getters & Queries
    @staticmethod
    def get_role_choices(org_id):
        query = models.Session.query(
            models.OrganizationRole).order_by(models.OrganizationRole.priority)
        if not current_user.super_admin:
            priority = current_user.role_for_org(org_id).priority
            query.filter(models.OrganizationRole.priority >= priority)
        return [(str(r.id), r.description) for r in query.all()]

    @staticmethod
    def get_invited_users(org_id):
        query = models.Session.query(
            models.User, models.Notification, models.Organization).join(
                models.Notification,
                models.User.id == models.Notification.user_to_id).join(
                    models.Organization,
                    models.Organization.id ==
                    models.Notification.organization_id).join(
                        models.NotificationType,
                        models.NotificationType.id ==
                        models.Notification.notification_type_id).filter(
                            sa.and_(
                                models.NotificationType.description ==
                                "Invitation to Join Organization",
                                models.Notification.organization_id == org_id,
                                models.Notification.accepted.is_(None),
                                models.Notification.acknowledged.is_(None),
                                models.Notification.declined.is_(None)))
        return query.all()

    @staticmethod
    def select_creation_form():
        if current_user.super_admin:
            return forms.OrgFormWithOwner(flask.request.form)
        return forms.OrgForm(flask.request.form)

    @staticmethod
    def query_users_with_type(org_id):
        with models.transaction() as session:
            query = session.query(models.User).join(
                models.OrganizationMember,
                models.User.id == models.OrganizationMember.user_id).join(
                    models.Organization,
                    models.Organization.id ==
                    models.OrganizationMember.organization_id).join(
                        models.OrganizationRole,
                        models.OrganizationRole.id ==
                        models.OrganizationMember.role_id).filter(
                            models.Organization.id == org_id)
            return query

    def get_leaders(self, org_id):
        org_users = self.query_users_with_type(org_id)
        org_admins_and_owners = org_users.filter(sa.or_(
            models.OrganizationRole.description ==
            'Owner',
            models.OrganizationRole.description ==
            'Organization Administrator'))
        return org_admins_and_owners.all()

    def get_members(self, org_id):
        org_users = self.query_users_with_type(org_id)
        org_members = org_users.filter(models.OrganizationRole.description ==
                                       'Member')
        return org_members.all()

    @staticmethod
    def document_upload(org_id, form):
        LOG.debug("Organizations cannot currently handle document uploads")

    def select_users_query(self, org_id, emails, texting):
        if emails:
            return self.query_users_with_email_opt_in(org_id)
        if texting:
            return self.query_users_with_phone(org_id)
        return self.query_users(org_id)

    def get_users(self, org_id, emails=False, texting=False):
        query = self.select_users_query(org_id, emails, texting)
        return query.all()

    def query_users_with_email_opt_in(self, org_id):
        query = self.query_users(org_id)
        users_query = query.filter(
            models.User.opt_in_emails == 1)
        return users_query

    def query_users_with_phone(self, org_id):
        query = self.query_users_with_type(org_id)
        users_query = query.filter(sa.and_(
            models.Organization.id == org_id,
            models.User.opt_in_texts == 1,
            models.User.phone_number.isnot(None)
        ))
        return users_query

    @staticmethod
    def query_users(org_id):
        with models.transaction() as session:
            org_users = session.query(
                models.User, models.OrganizationRole).join(
                    models.OrganizationMember,
                    models.User.id == models.OrganizationMember.user_id).join(
                        models.Organization,
                        models.OrganizationMember.organization_id ==
                        models.Organization.id).join(
                            models.OrganizationRole,
                            models.OrganizationMember.role_id ==
                            models.OrganizationRole.id).filter(
                                models.Organization.id == org_id).order_by(
                                    models.OrganizationRole.priority)
        return org_users

    @staticmethod
    def get_member(org_id, user_id):
        with models.transaction() as session:
            existing_member = session.query(models.OrganizationMember).filter(
                models.OrganizationMember.organization_id == org_id).filter(
                    models.OrganizationMember.user_id == user_id)
            return existing_member.first()

    @staticmethod
    def get_meetings(org_id):
        LOG.debug("Organizations cannot currently handle meetings %s", org_id)

    @staticmethod
    def groups_sort(org_id, group_ids):
        groups_order = {}
        for order, group_id in enumerate(group_ids):
            groups_order[group_id] = order

        organization_groups = models.Session.query(
            models.OrganizationGroup
        ).filter_by(
            organization_id=org_id
        ).filter(
            models.OrganizationGroup.group_id.in_(groups_order.keys())
        ).all()

        with models.transaction() as session:
            for og in organization_groups:
                og.order = groups_order[str(og.group_id)]
                session.add(og)
            session.commit()

    # Other Helpers
    def custom_email_form(self, data_id, form):
        emailable = self.get_users(data_id, emails=True)
        choices = [("all", "Email All Users")]
        choices += [(u.id, u.full_name) for u, _ in emailable]
        LOG.debug("EMAIL USERS: %s", choices)
        form.recipient.choices = choices
        return form

    def join_request_handler(self, org_leaders, org_id):
        with models.transaction() as session:
            notification_type = session.query(
                models.NotificationType).filter(
                    models.NotificationType.description ==
                    'Organization Join Request').first()
            reminder = None
            for user in org_leaders:
                notification = models.Notification(
                    user_to_id=user.id,
                    user_from_id=current_user.id,
                    notification_type_id=notification_type.id,
                    organization_id=org_id)
                reminder = self.send_notification(notification)
            mail_to = ','.join([u.email for u
                                in org_leaders])
            email_type = email.OrgJoinRequestEmail()
            org = models.Organization.get(org_id)
            self.send_email(email_type, current_user.email, mail_to, reminder,
                            org=org)
            flask.flash(
                'Request to join organization successfully sent!', 'success')

    @staticmethod
    def populate_org(org_to_populate, form):
        org_to_populate.name = form.name.data
        org_to_populate.vanity_name = form.custom_url.data
        org_to_populate.description = form.description.data
        org_to_populate.service_times_description = form.service_times.data
        org_to_populate.date_established = form.date_founded.data
        org_to_populate.show_address = form.show_address.data
        org_to_populate.address = models.Address(
            street_address=form.street_address.data,
            city=form.city.data,
            state=form.state.data,
            zip_code=form.zip_code.data)
        return org_to_populate

    @staticmethod
    def populate_primary_form(form, org_object):
        o = org_object
        form.name.data = o.name
        form.custom_url.data = o.vanity_name
        form.description.data = o.description
        form.service_times.data = o.service_times_description
        form.date_founded.data = o.date_established
        form.show_address.data = o.show_address
        if o.address:
            form.street_address.data = o.address.street_address
            form.city.data = o.address.city
            form.state.data = o.address.state
            form.zip_code.data = o.address.zip_code

    @staticmethod
    def google_doc_add(org_id, googledoc):
        LOG.debug("Organizations cannot currently handle Google Documents")

    def creation_workflow(self, form):
        if current_user.super_admin:
            return self.create_new_organization_workflow(form)
        return self.request_new_organization_workflow(form)

    def create_new_organization_workflow(self, form):
        try:
            address = models.User.get_email_from_full_name_and_email(
                form.owner.data)
            u = models.User.get_by_email(address)
            LOG.debug(
                'New organization owner: %s', u.full_name_and_email)
            orgr = models.OrganizationRole.get_by_description('Owner')
            org = models.Organization()
            self.populate_org(org, form)
            org.activated_at = datetime.datetime.utcnow()
            with models.transaction() as session:
                session.add(org)
                session.commit()
                om = models.OrganizationMember(
                    user_id=u.id,
                    organization_id=org.id,
                    role_id=orgr.id)
                session.add(om)
            flask.flash('You successfully created the organization', 'success')
            return flask.redirect(flask.url_for('.show', org_id=org.id))
        except Exception:
            LOG.exception('Failed to create organization')
            flask.flash('There was an error creating the organization',
                        'danger')
            return flask.redirect(flask.url_for('index'))

    def request_new_organization_workflow(self, form):
        try:
            user = current_user
            LOG.debug(
                "New organization owner: %s", user.full_name_and_email)
            org = models.Organization()
            self.populate_org(org, form)
            with models.transaction() as session:
                super_admins = session.query(models.User).filter(
                    models.User.super_admin == sa.sql.expression.true()).all()
                if super_admins:
                    LOG.debug('Super admins to be notified of org'
                              ' creation request: %s', super_admins)
                    session.add(org)
                    session.commit()
                    LOG.debug('Organization: %s:%s', org.id, org.name)
                    ocr = models.NotificationType.get_by_description(
                        'Organization Creation Request')
                    reminder = None
                    for admin in super_admins:
                        notification = models.Notification(
                            user_to_id=admin.id,
                            user_from_id=current_user.id,
                            notification_type_id=ocr.id,
                            organization_id=org.id)
                        reminder = self.send_notification(notification)
                        LOG.debug('Org creation notification sent to %s',
                                  admin.email)
                    mail_to = ','.join([u.email for u in super_admins])
                    email_type = email.OrgCreationRequestEmail()
                    self.send_email(email_type, current_user.email, mail_to,
                                    reminder, org=org)
                    flask.flash(
                        'Organization creation request sent successfully.',
                        'success')
                else:
                    LOG.debug(
                        'Unable to send organization request for %s due to no'
                        ' super admins presnet. Organization name: %s',
                        current_user.email, org.name)
                    flask.flash(
                        'No super admins present, unable to send organization'
                        ' creation request. Please try again later.', 'danger')
                    return flask.redirect(flask.url_for('index'))
        except Exception:
            LOG.exception('Failed to request organization creation')
            flask.flash('There was an error requesting organization creation',
                        'danger')
        return flask.redirect(flask.url_for('index'))

    def show(self, org):
        if not org or org.activated_at is None:
            flask.flash('Organization not found. Please try again', 'danger')
            return flask.redirect(flask.url_for('index'))
        cloudinary = dict(
            entity_id=org.id,
            entity_type='organization',
            **CloudinaryHandler.cloudinary_elements())

        ef = forms.MassEmailForm()
        email_form = self.custom_email_form(org.id, ef)
        wtforms = {
            'mass_email': email_form,
            'confirm': forms.ConfirmForm(flask.request.form)}
        context = {
            'cloudinary': cloudinary,
            'env': CONF.get('environment'),
            'google_api_key': CONF.get('google.api.key'),
            'invited_users': self.get_invited_users(org.id),
            'join_request_url': flask.url_for('orgs.join_request',
                                              org_id=org.id),
            'members': self.get_users(org.id),
            'org': org,
            'video_extensions': tuple(VIDEO_EXTENSIONS),
            'wtforms': wtforms}
        return flask.render_template('organization/view.html', **context)

    def handle_invite(self, content, user):
        org_id = content.get('org_id')
        org_role_id = content.get('org_role_id')
        if org_id:
            with models.transaction() as session:
                try:
                    if not self.get_member(org_id, user.id):
                        om = models.OrganizationMember(
                            organization_id=org_id,
                            user_id=user.id,
                            role_id=org_role_id)
                        session.add(om)
                    else:
                        flask.flash(
                            'User already member of organization', 'info')
                except Exception:
                    LOG.exception('Failed to add member to organization')
                    models.Session.rollback()
                    flask.flash(
                        'There was an error associating to your invited'
                        ' organization. Please have person re-add you.',
                        'danger')
                    return flask.redirect(flask.url_for('login'))

    def notify_join(self, user_to, org):
        try:
            with models.transaction() as session:
                nt = session.query(
                    models.NotificationType).filter(
                        models.NotificationType.description.like(
                            '%Join Org%')).first()
                notification = models.Notification(
                    notification_type_id=nt.id,
                    user_to_id=user_to.id,
                    user_from_id=current_user.id,
                    organization_id=org.id)
                reminder = self.send_notification(notification)
                email_type = email.InviteExistingUserToOrgEmail()
                self.send_email(email_type, current_user.email, user_to.email,
                                reminder, org=org)
                flask.flash('Notification sent to member for acceptance or'
                            ' rejection.', 'success')
        except Exception:
            LOG.exception('Failed to invite member to org %s', org.id)
            flask.flash('There was an error adding the member. Please try'
                        ' again later.', 'danger')
