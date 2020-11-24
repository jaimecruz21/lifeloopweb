from zoomus import ZoomClient

from lifeloopweb import (
    config, exception as exc, logging)
from lifeloopweb.db import models
from lifeloopweb.helpers.base_helper import Helper


MEETING_DRIVER = None
CONF = config.CONF
LOG = logging.get_logger(__name__)

helper = Helper()


class MeetingDriver():
    def schedule_meeting(self, **meeting_info):
        raise NotImplementedError("Parent MeetingDriver has no implementation")


class ZoomMeetingDriver(MeetingDriver):
    # ZOOM REST API DOCS: https://zoom.us/developer/overview/rest-user-api
    PRO_USER_TYPE = 2
    USER_ID_INVALID_OR_MISSING = 1010
    SNS_ZOOM_LOGIN_TYPE = 99

    def __init__(self):
        LOG.debug("Initialzing ZoomDriver")
        self._api_key = CONF.get("zoom.api.key")
        self._api_secret = CONF.get("zoom.api.secret")
        self._client = ZoomClient(self._api_key, self._api_secret)
        super().__init__()

    def schedule_meeting(self, **meeting_info):
        LOG.debug("Scheduling meeting")
        current_user = meeting_info.get('current_user')
        self.handle_current_user(current_user)
        cohosts = meeting_info.get('cohosts')
        self.handle_cohosts(cohosts)
        LOG.debug("User %s has zoom user id %s",
                  current_user.full_name, current_user.zoom_user_id)
        try:
            result = self.create_meeting(**meeting_info)
            LOG.debug("RESULT: create meeting: %s", result.json())
            if (result.json().get('error') and
                    result.json()['error']['code'] ==
                    self.USER_ID_INVALID_OR_MISSING):
                current_user.zoom_user_id = None
                self.handle_current_user(current_user)
                result = self.create_meeting(**meeting_info)
            return result.json()
        except Exception:
            LOG.exception("Issue creating zoom meeting for user: %s",
                          current_user.full_name_and_email)
            return None

    def handle_current_user(self, current_user):
        if not current_user:
            raise NoUserException()
        if not current_user.zoom_user_id:
            self.handle_zoom_information(current_user)

    def handle_cohosts(self, cohosts):
        if cohosts:
            for c in cohosts:
                if not c.user.zoom_user_id:
                    LOG.debug("Createing zoom id for %s", c.user.email)
                    self.handle_zoom_information(c.user)

    def formatted_cohosts(self, cohosts):
        if not cohosts:
            return None
        return ','.join([str(c.user.zoom_user_id) for c in cohosts])

    def create_meeting(self, **meeting_info):
        current_user = meeting_info.get('current_user')
        cohosts = meeting_info.get('cohosts')
        utc_start_time = helper.get_utc_date_time(
            current_user.timezone,
            meeting_info.get('start_time'))
        result = self._client.meeting.create(
            host_id=current_user.zoom_user_id,
            topic=meeting_info.get('topic', 'Topic Placeholder'),
            type=meeting_info.get(
                'type', models.ZoomMeeting.SCHEDULED_MEETING),
            duration=meeting_info.get('duration', 60),
            option_jbh='false',
            option_alternative_host_ids=self.formatted_cohosts(cohosts),
            timezone=current_user.timezone,
            start_time=utc_start_time)
        return result

    def update_meeting(self, **meeting_info):
        LOG.debug("Updating meeting")
        current_user = meeting_info.get('current_user')
        self.handle_current_user(current_user)
        cohosts = meeting_info.get('cohosts')
        self.handle_cohosts(cohosts)
        try:
            meeting_id = meeting_info.get('meeting_id')
            if not meeting_id:
                raise NoMeetingIdException()
            utc_start_time = helper.get_utc_date_time(
                current_user.timezone,
                meeting_info.get('start_time'))
            result = self._client.meeting.update(
                id=meeting_id,
                host_id=current_user.zoom_user_id,
                topic=meeting_info.get('topic', 'Topic Placeholder'),
                type=meeting_info.get(
                    'type', models.ZoomMeeting.SCHEDULED_MEETING),
                option_jbh='false',
                option_alternative_host_ids=self.formatted_cohosts(cohosts),
                duration=meeting_info.get('duration', 60),
                timezone=current_user.timezone,
                start_time=utc_start_time)
            return result.json()
        except Exception:
            LOG.exception("Issue updating zoom meeting for user: %s",
                          current_user.full_name_and_email)
            raise

    def delete_meeting(self, **meeting_info):
        LOG.debug("Deleting meeting")
        current_user = meeting_info.get('current_user')
        if not current_user:
            raise NoUserException()
        if not current_user.zoom_user_id:
            self.handle_zoom_information(current_user)
        try:
            meeting_id = meeting_info.get('meeting_id')
            if not meeting_id:
                raise NoMeetingIdException()
            result = self._client.meeting.delete(
                id=meeting_id,
                host_id=current_user.zoom_user_id)
            LOG.debug("Deletion HTTP status code: %s", result.status_code)
            return result.json()
        except Exception:
            LOG.exception("Issue creating zoom meeting for user: %s",
                          current_user.full_name_and_email)
            raise

    def handle_zoom_information(self, user):
        try:
            result = self._client.user.get_by_email(
                email=user.email, login_type=self.SNS_ZOOM_LOGIN_TYPE)
            LOG.debug("RESULT: get zoom client by email: %s", result.json())
            if result.json().get('error'):
                result = self._client.user.cust_create(
                    email=user.email,
                    type=self.PRO_USER_TYPE,
                    first_name=user.first_name,
                    last_name=user.last_name)
                LOG.debug("RESULT: create zoom customer: %s", result.json())
        except Exception:
            LOG.exception("Issue creating zoom customer for user: %s",
                          user.full_name_and_email)
            raise
        try:
            # TODO: move database update out into flask route
            # means we need to detect user property in flask route, update
            # user and then call schedule_meeting
            with models.transaction() as session:
                user.zoom_user_id = result.json()['id']
                session.add(user)
        except Exception:
            LOG.exception("Issue adding zoom_user_id to user: %s",
                          user.full_name_and_email)
            raise


def meeting_driver():
    return MEETING_DRIVER


if not MEETING_DRIVER:
    driver = CONF.get("meeting.driver")
    if driver.lower() == "zoommeetingdriver":
        MEETING_DRIVER = ZoomMeetingDriver()


class NoMeetingIdException(exc.LifeloopException):
    message = ("No meeting id provided when trying to update/delete meeting")


class NoUserException(exc.LifeloopException):
    message = ("No user logged in when trying to create meeting")
