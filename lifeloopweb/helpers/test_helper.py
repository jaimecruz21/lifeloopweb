#!/usr/bin/env python

import math
import datetime
from urllib.parse import urlparse, urljoin
import pytz
import sqlalchemy as sa
import flask
from flask_login import current_user

from lifeloopweb import exception as exc, constants, logging, sms
from lifeloopweb.db import models

LOG = logging.get_logger(__name__)


class Helper(object):
    @staticmethod
    def is_safe_url(target):
        ref_url = urlparse(flask.request.host_url)
        test_url = urlparse(urljoin(flask.request.host_url, target))
        return (test_url.scheme in ('http', 'https') and
                ref_url.netloc == test_url.netloc)

    @staticmethod
    def seconds(value):
        # Just for clarity when used in a function
        return value

    @staticmethod
    def minutes(value_in_seconds):
        return value_in_seconds * 60

    def hours(self, value_in_seconds):
        return self.minutes(value_in_seconds) * 60

    def days(self, value_in_seconds):
        return self.hours(value_in_seconds) * 24

    @staticmethod
    def _get_model(model, field, value):
        return model.get_by(field, value)

    def get_or_404(self, model, field, value):
        record = self._get_model(model, field, value)
        if not record:
            flask.abort(404)
        return record

    @staticmethod
    def get_utc_date_time(timezone, dt):
        if not dt:
            return datetime.datetime.utcnow()
        if not timezone:
            raise exc.UserTimezoneMissing()
        t = pytz.timezone(timezone).localize(dt)
        return t.astimezone(pytz.UTC)

    @staticmethod
    def datetime_offset(dt, timezone=None):
        if not timezone:
            return dt.strftime(constants.DATE_TIME_FORMAT)
        tz = pytz.timezone(timezone)
        return pytz.utc.localize(
            dt, is_dst=None).astimezone(tz).strftime(
                constants.DATE_TIME_FORMAT)

    def date_only_offset(self, dt, timezone=None):
        converted_dt = self.datetime_offset(dt, timezone)
        converted_dt = datetime.datetime.strptime(
            converted_dt, constants.DATE_TIME_FORMAT)
        return converted_dt.strftime(constants.DATE_FORMAT)

    def time_only_offset(self, dt, timezone=None):
        converted_dt = self.datetime_offset(dt, timezone)
        converted_dt = datetime.datetime.strptime(
            converted_dt, constants.DATE_TIME_FORMAT)
        return converted_dt.strftime(constants.TIME_FORMAT)

    def day_of_week(self, dt, timezone=None):
        converted_dt = self.datetime_offset(dt, timezone)
        converted_dt = datetime.datetime.strptime(
            converted_dt, constants.DATE_TIME_FORMAT)
        return converted_dt.strftime(constants.DAY_OF_WEEK_FORMAT)

    @staticmethod
    def seconds_to_hours_and_minutes(s):
        h, m = divmod(s, 60)
        return '%d:%02d' % (h, m)

    def get_all_emails(self, data_id):
        group_member_emails = ''
        group_users = self.get_users(data_id, emails=True)
        for user, _, _ in group_users:
            group_member_emails += user.email + ', '
        return group_member_emails

    @staticmethod
    def send_notification(notification):
        verified_notification = notification.prevent_duplicate()
        if verified_notification:
            with models.transaction() as session:
                session.add(verified_notification)
        else:
            return 'blocked'
        return bool(verified_notification != notification)

    @staticmethod
    def send_email(email_type, mail_from, mail_to, reminder, group=None,
                   org=None):
        if reminder == 'blocked':
            return
        kwargs = {'org': org, 'group': group, 'reminder': reminder}
        email_type.send(mail_from, mail_to, **kwargs)

    @staticmethod
    def send_text_message(message, flash=True):
        if not message:
            flask.flash(
                'There are not currently any group members that are accepting'
                ' text messages. No message sent. Please try again shortly.',
                'danger')
            LOG.debug("No message with recipient was provided.")
            return
        try:
            # TODO: need to wrap this data in a cleaner
            # (NEVER TRUST USER INPUT)
            for phone_number, text in message.items():
                sms.sms_driver().send_text(phone_number, text)
                if flash:
                    flask.flash(
                        'You successfully sent your text message.', 'success')
        except Exception:
            LOG.debug("Text message failed to send.")
            if flash:
                flask.flash(
                    'We could not send the text message(s). Sorry for the'
                    ' inconvenience. Please try again shortly.', 'danger')

    def unique_group_name(self, org_id, name):
        org_groups = self.get_org_groups(org_id)
        for og in org_groups:
            if name == og.name:
                return False
        return True

    @staticmethod
    def get_org_groups(org_id):
        with models.transaction() as session:
            org_groups = session.query(models.Group).join(
                models.OrganizationGroup,
                models.OrganizationGroup.group_id ==
                models.Group.id).join(
                    models.Organization,
                    models.Organization.id ==
                    models.OrganizationGroup.organization_id).filter(
                        models.Organization.id == org_id)
            return org_groups.all()

    @staticmethod
    def leader_alert_text(leader, sender, group, zoom_meeting):
        message_format_args = [
            leader.first_name,
            sender.first_name,
            sender.last_name,
            group.name,
            zoom_meeting.topic
        ]
        message = ('{}, this is a courtesy message from LifeLoop.Live to'
                   ' inform you that {} {} has sent a mass reminder text to {}'
                   ' about their meeting: {}.'.format(*message_format_args))
        return message

    @staticmethod
    def meeting_creator_alert_text(starter, group, zoom_meeting):
        message_format_args = [
            starter.first_name,
            group.name,
            zoom_meeting.topic,
            zoom_meeting.info(current_user.timezone),
            zoom_meeting.start_url
        ]
        message = (
            '{}, members of {} have been notified via text about your'
            ' LifeLoop.Live meeting: {}. To start this meeting, please go to'
            ' the link below, or start the meeting from LifeLoop.Live at the'
            ' start time ({}). {}'.format(*message_format_args))
        return message

    @staticmethod
    def meeting_join_text(member, group, zoom_meeting):
        duration_hours = math.floor(zoom_meeting.duration/60)
        duration_minutes = zoom_meeting.duration - (duration_hours*60)
        message_format_args = [
            member.first_name,
            group.name,
            zoom_meeting.topic
        ]
        message = (
            '{}, this is a reminder that {} has scheduled a LifeLoop.Live'
            ' meeting entitled: {}.')
        if duration_hours:
            message += ' The meeting will last {} hour'
            message_format_args.append(duration_hours)
        if duration_hours > 1:
            message += 's'
        if duration_hours and duration_minutes:
            message += ' and'
        if duration_minutes:
            message += ' {} minutes'
            message_format_args.append(duration_minutes)
        message += ', and is scheduled for {}. Join this meeting by going to {}'
        message_format_args.extend([
            zoom_meeting.info(current_user.timezone), zoom_meeting.join_url])
        return message.format(*message_format_args)

    @staticmethod
    def get_meeting_by_id(meeting_id):
        with models.transaction() as session:
            meeting_result = session.query(models.ZoomMeeting).filter(
                models.ZoomMeeting.id == meeting_id).filter(
                    sa.or_(
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
            return meeting_result.first()
