#!/usr/bin/env python
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
import datetime
import flask
from flask_login import current_user
import sqlalchemy as sa

from lifeloopweb import email, filehandler, config, logging, exception as exc
from lifeloopweb.helpers.base_helper import Helper
from lifeloopweb.helpers.org_helper import OrgHelper
from lifeloopweb.db import models

CONF = config.CONF
LOG = logging.get_logger(__name__)
org_helper = OrgHelper()


class GroupHelper(Helper):
    # DB Queries and Getters
    def get_leaders(self, group_id, texting=False):
        query = self.select_users_query(group_id, texting)
        group_leaders = query.filter(
            models.GroupRole.description == 'Group Leader')
        return group_leaders.all()

    @staticmethod
    def get_member(group_id, user_id):
        with models.transaction() as session:
            group_member = session.query(models.GroupMember).filter(
                models.GroupMember.user_id == user_id).filter(
                    models.GroupMember.group_id == group_id)
            return group_member.first()

    def get_members(self, group_id, texting=False):
        query = self.select_users_query(group_id, texting)
        group_members = query.filter(
            models.GroupRole.description == 'Member')
        return group_members.all()

    @staticmethod
    def get_role_choices(priority=None):
        query = models.Session.query(
            models.GroupRole).order_by(models.GroupRole.priority)
        if priority:
            query.filter(models.GroupRole.priority >= priority)
        return [(str(r.id), r.description) for r in query.all()]

    def get_users(self, group_id, texting=False, emails=False):
        query = self.select_users_query(group_id, texting, emails)
        return query.all()

    @staticmethod
    def get_invited_users(group_id):
        query = models.Session.query(
            models.User, models.Notification, models.Group).join(
                models.Notification,
                models.User.id == models.Notification.user_to_id).join(
                    models.Group,
                    models.Group.id ==
                    models.Notification.group_id).join(
                        models.NotificationType,
                        models.NotificationType.id ==
                        models.Notification.notification_type_id).filter(
                            sa.and_(
                                models.NotificationType.description ==
                                "Invitation to Join Group",
                                models.Notification.group_id == group_id,
                                models.Notification.accepted.is_(None),
                                models.Notification.acknowledged.is_(None),
                                models.Notification.declined.is_(None)))
        return query.all()

    @staticmethod
    def get_meetings(group_id):
        query = models.Session.query(models.ZoomMeeting).filter(
            models.ZoomMeeting.group_id == group_id).filter(sa.or_(
                sa.and_(
                    models.ZoomMeeting.repeat_type ==
                    models.ZoomMeeting.SCHEDULED_MEETING,
                    sa.sql.func.ADDDATE(
                        models.ZoomMeeting.meeting_start,
                        sa.sql.expression.text(
                            "interval zoom_meetings.duration minute")) >=
                    datetime.datetime.utcnow()),
                sa.and_(
                    models.ZoomMeeting.repeat_type ==
                    models.ZoomMeeting.REPEATED_MEETING,
                    sa.or_(
                        models.ZoomMeeting.repeat_end_date >=
                        datetime.datetime.utcnow().date(),
                        models.ZoomMeeting.repeat_end_date.is_(
                            None))))).order_by(
                                models.ZoomMeeting.meeting_start).limit(
                                    models.ZoomMeeting.LIST_LIMIT)
        return query.all()

    @staticmethod
    def get_unaffiliated_orgs_for_group(group_id):
        # TODO Move set difference into db query (instead of memory)
        all_orgs = models.Session.query(models.Organization).filter(
            models.Organization.activated_at.isnot(None)).all()
        group_orgs = models.Session.query(models.Organization).join(
            models.OrganizationGroup,
            models.OrganizationGroup.organization_id ==
            models.Organization.id).join(
                models.Group,
                models.OrganizationGroup.group_id == models.Group.id).filter(
                    sa.and_(models.Organization.activated_at.isnot(None),
                            models.Group.id == group_id)).all()
        other_orgs = sorted(list(set(all_orgs) - set(group_orgs)))
        return other_orgs

    @staticmethod
    def query_users(group_id):
        with models.transaction() as session:
            users_query = session.query(
                models.User, models.GroupMember, models.GroupRole).join(
                    models.GroupMember,
                    models.User.id == models.GroupMember.user_id).join(
                        models.Group,
                        models.Group.id ==
                        models.GroupMember.group_id).join(
                            models.GroupRole,
                            models.GroupRole.id ==
                            models.GroupMember.role_id).filter(
                                models.Group.id == group_id).order_by(
                                    models.GroupRole.priority)
            return users_query

    def query_users_with_email_opt_in(self, group_id):
        query = self.query_users(group_id)
        users_query = query.filter(
            models.User.opt_in_emails == 1)
        return users_query

    @staticmethod
    def query_users_with_phone(group_id):
        with models.transaction() as session:
            users_query = session.query(models.User).join(
                models.GroupMember,
                models.User.id == models.GroupMember.user_id).join(
                    models.Group,
                    models.Group.id == models.GroupMember.group_id).join(
                        models.GroupRole,
                        models.GroupMember.role_id ==
                        models.GroupRole.id).filter(
                            sa.and_(
                                models.Group.id == group_id,
                                models.User.opt_in_texts == 1,
                                models.User.phone_number.isnot(None)))
            return users_query

    def select_users_query(self, group_id, texting=False, emails=False):
        if texting:
            return self.query_users_with_phone(group_id)
        if emails:
            return self.query_users_with_email_opt_in(group_id)
        return self.query_users(group_id)

    # Other Helpers
    def custom_email_form(self, data_id, form):
        emailable = self.get_users(data_id, emails=True)
        choices = [("all", "Email All Users")]
        choices += [(u.id, u.full_name) for u, _, _ in emailable]
        LOG.debug("EMAIL USERS: %s", choices)
        form.recipient.choices = choices
        return form

    def creation_workflow(self, form, org):
        with models.transaction() as session:
            if form.user_is_leader.data:
                leader = current_user
            else:
                address = models.User.get_email_from_full_name_and_email(
                    form.owner.data)
                leader = models.User.get_by_email(address)
            group_leaders = org.group_leaders
            if (leader not in group_leaders) and not org.is_in_trial() and (org.available_licenses < 1):
                return self.need_leaders(org.id)
            new_group = models.Group(
                name=form.name.data,
                description=form.description.data,
                member_limit=form.member_limit.data,
                privacy_setting_id=form.privacy_settings.data,
                anonymous=form.anonymous.data,
                gender_focus=form.gender_focus.data)
            if form.age_range.data:
                new_group.age_range_id = form.age_range.data.id
            if form.group_category.data:
                new_group.group_type_id = form.group_category.data.id
            session.add(new_group)
        with models.transaction() as session:
            organization_group = models.OrganizationGroup(
                organization_id=form.org.data,
                group_id=new_group.id)
            session.add(organization_group)
            new_group_meet_times = []
            for group_meet_time_type in form.meet_times.data:
                new_group_meet_time = models.GroupMeetTime(
                    group_id=new_group.id,
                    meet_time_type_id=group_meet_time_type.id)
                new_group_meet_times.append(new_group_meet_time)
            if new_group_meet_times:
                session.add_all(new_group_meet_times)
            group_role = session.query(models.GroupRole).filter(
                models.GroupRole.description == 'Group Leader').first()
            group_member = models.GroupMember(
                group_id=new_group.id,
                user_id=leader.id,
                role_id=group_role.id)
            form.owner.default = current_user.id
            session.add(group_member)
        flask.flash("Group {} created successfully".format(form.name.data))
        return flask.redirect(flask.url_for(
            '.show', group_id=new_group.id))

    @staticmethod
    def google_doc_add(group_id, googledoc):
        with models.transaction() as session:
            d = models.GroupDocument(
                group_id=group_id,
                friendly_name=googledoc.filename.data,
                file_url=googledoc.link.data)
            session.add(d)
        flask.flash('Link Successfully Added!', 'success')
        return

    @staticmethod
    def group_creation_org_choices(org_id=None):
        with models.transaction() as session:
            if org_id:
                orgs = session.query(models.Organization).filter(
                    models.Organization.id == org_id).all()
            else:
                orgs_where_owner_or_admin_query = session.query(
                    models.Organization).join(
                        models.OrganizationMember,
                        models.OrganizationMember.organization_id ==
                        models.Organization.id).join(
                            models.User,
                            models.User.id ==
                            models.OrganizationMember.user_id).join(
                                models.OrganizationRole,
                                models.OrganizationRole.id ==
                                models.OrganizationMember.role_id).filter(
                                    models.User.id == current_user.id).filter(
                                        models.OrganizationRole.description.in_((
                                            'Owner', 'Organization Administrator',
                                            'Group Administrator')))
                orgs_where_owner_or_admin = orgs_where_owner_or_admin_query.all()
                orgs_where_group_leader_of_group = session.query(
                    models.Organization).join(
                        models.OrganizationGroup,
                        models.OrganizationGroup.organization_id ==
                        models.Organization.id).join(
                            models.Group,
                            models.Group.id ==
                            models.OrganizationGroup.group_id).join(
                                models.GroupMember,
                                models.GroupMember.group_id ==
                                models.Group.id).join(
                                    models.User,
                                    models.User.id ==
                                    models.GroupMember.user_id).join(
                                        models.GroupRole,
                                        models.GroupRole.id ==
                                        models.GroupMember.role_id).filter(
                                            models.User.id ==
                                            current_user.id).filter(
                                                (models.GroupRole.description ==
                                                 'Group Leader')).all()
                orgs = list(set(orgs_where_owner_or_admin) |
                            set(orgs_where_group_leader_of_group))
            return [(o.id, o.name) for o in orgs]

    @staticmethod
    def document_upload(group_id, form):
        if 'file' not in flask.request.files:
            flask.flash('Please provide a file', 'danger')
            return flask.redirect(flask.url_for('.show', group_id=group_id))
        doc = flask.request.files['file']
        try:
            doc_handler = filehandler.S3FileHandler(doc, form.filename.data)
            url = doc_handler.save()
            with models.transaction() as session:
                d = models.GroupDocument(
                    group_id=group_id,
                    friendly_name=doc_handler.filename,
                    file_url=url)
                session.add(d)
            flask.flash('You successfully uploaded a document!', 'success')
            return flask.redirect(flask.url_for('.show', group_id=group_id))
        except exc.InvalidFileExtensionException as e:
            LOG.exception("Invalid File Extension")
            flask.flash(str(e), 'danger')
        except exc.FileAlreadyExists as e:
            LOG.exception("File Already Exists")
            flask.flash(str(e), 'danger')
        except Exception:
            LOG.exception(
                "Failed to save the document for group %s", str(group_id))
            flask.flash('There was an error uploading the document. Please try'
                        ' again later.', 'danger')
        return flask.redirect(flask.url_for('.show', group_id=group_id))

    def show(self, group):
        pass

    @staticmethod
    def handle_invite(content, user):
        group_id = content.get('group_id')
        group_role_id = content.get('group_role_id')
        error_message = (
            "There was an error associating to your invited group."
            " Please have person re-add you.")
        if group_id:
            with models.transaction() as session:
                try:
                    gm = models.GroupMember(
                        group_id=group_id,
                        user_id=user.id,
                        role_id=group_role_id)
                    session.add(gm)
                except Exception:
                    LOG.exception("Error adding invited user to group")
                    models.Session.rollback()
                    flask.flash(error_message, 'danger')
        else:
            flask.flash(error_message, 'danger')
        return flask.redirect(flask.url_for("login"))

    def join_request_handler(self, group_leaders, group_id):
        notification_type = models.NotificationType.get_by_description(
            'Group Join Request')
        for group_leader in group_leaders:
            notification = models.Notification(
                user_to_id=group_leader.id,
                user_from_id=current_user.id,
                notification_type_id=notification_type.id,
                group_id=group_id)
            reminder = self.send_notification(notification)
        group = models.Group.get(group_id)
        if group:
            mail_to = ','.join([u.email for u in group_leaders])
            email_type = email.GroupJoinRequestEmail()
            self.send_email(email_type, current_user.email, mail_to, reminder,
                            group=group)
            flask.flash('Request to join group successfully sent!', 'success')
        else:
            flask.flash('No group found', 'danger')
            return flask.redirect(flask.url_for('.show', group_id=group_id))

    def notify_join(self, user_to, group):
        try:
            with models.transaction() as session:
                nt = session.query(
                    models.NotificationType).filter(
                        models.NotificationType.description.like(
                            '%Join Group%')).first()
                notification = models.Notification(
                    notification_type_id=nt.id,
                    user_to_id=user_to.id,
                    user_from_id=current_user.id,
                    group_id=group.id)
                reminder = self.send_notification(notification)
                email_type = email.InviteExistingUserToGroupEmail()
                self.send_email(email_type, current_user.email, user_to.email,
                                reminder, group=group)

                flask.flash("Notification sent to member for acceptance or"
                            " rejection.", "success")
        except Exception:
            LOG.exception("Failed to invite member to group %s", group.id)
            flask.flash("There was an error adding the member. Please try"
                        " again later.", "danger")

    @staticmethod
    def populate_primary_form(form, group_info):
        form.privacy_settings.default = group_info.privacy_setting_id
        form.anonymous.default = group_info.anonymous
        form.age_range.default = group_info.age_range
        form.gender_focus.default = group_info.gender_focus
        form.group_category.default = group_info.group_type
        form.meet_times.default = group_info.meet_times
        form.process()
        form.description.data = group_info.description
        form.member_limit.data = group_info.member_limit
        return form

    @staticmethod
    def select_creation_form():
        LOG.debug("This Function is Not Currently Used in Groups")
