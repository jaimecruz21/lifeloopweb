#!/usr/bin/env python
# pylint: disable=no-value-for-parameter,too-many-nested-blocks

import contextlib
import datetime
import functools
import re
from abc import abstractmethod

import sqlalchemy as sa
from sqlalchemy import event, exc, func, select
from sqlalchemy.ext import declarative
from sqlalchemy.ext import hybrid
from sqlalchemy import orm
import sqlalchemy_utils

from lifeloopweb import config, constants, exception, logging, renders, subscription
from lifeloopweb.db import utils as db_utils
from lifeloopweb.webpack import webpack
from lifeloopweb.helpers.base_helper import Helper
from flask_login import UserMixin

LOG = logging.get_logger(__name__)
CONF = config.CONF

helper = Helper()

TABLE_KWARGS = {"mysql_engine": "InnoDB",
                "mysql_charset": "utf8",
                "mysql_collate": "utf8_general_ci"}

DB_NAME = "lifeloopweb_{}".format(CONF.get("ENVIRONMENT"))

# TODO(mdietz): when this comes from a configuration, we need to
#            force the charset to utf8
ENGINE_URL = CONF.get("DB_ENGINE_URL")
if not ENGINE_URL:
    ENGINE_URL = ("mysql+pymysql://root:@127.0.0.1/"
                  "{}?charset=utf8".format(DB_NAME))

connection_debug = CONF.get("database.connection.debug")
if connection_debug.lower() not in ["true", "false"]:
    raise exception.InvalidConfigValue(value=connection_debug,
                                       key="database.connection.debug")

connection_debug = connection_debug.lower() == "true"
connection_pool_size = int(CONF.get("database.connection.poolsize"))
connection_overflow_pool = int(CONF.get("database.connection.overflowpool"))
# NOTE: MySQL defaults to 8 hour connection timeouts. It's possible that
#      docker-compose or our hosting provider will sever connections sooner.
#      if we see "MySQL has gone away" tweaking this variable is the thing
#      to revisit
connection_pool_recycle = int(CONF.get("database.connection.poolrecycle"))

engine_kwargs = {}
if "sqlite" not in ENGINE_URL:
    engine_kwargs = {
        "pool_size": connection_pool_size,
        "max_overflow": connection_overflow_pool,
        "pool_recycle": connection_pool_recycle}

engine = sa.create_engine(ENGINE_URL, echo=connection_debug,
                          **engine_kwargs)
SessionFactory = orm.sessionmaker(bind=engine, expire_on_commit=False,
                                  autocommit=False, autoflush=True)

# TODO use of the scoped session needs to be evaluated against
#     greenthreading servers like gunicorn and uwsgi. The scope
#     by default is to thread local, as in threading.local
#     and not the greenthread specifically. Things that use greenthreads
#     have to be gt aware, so really we may just do Scoped and Unscoped
#     sessions. Alternatively, we hack eventlet to attach the scope there
#     http://docs.sqlalchemy.org/en/latest/orm/contextual.html#using-custom-created-scopes
ScopedSession = orm.scoped_session(SessionFactory)
Session = ScopedSession


# TODO We may only want to do this conditionally. I've used it in the past
#     but I think the pool_recycling may be enough
@event.listens_for(engine, "engine_connect")
def ping_connection(connection, branch):
    if branch:
        return

    save_should_close_with_result = connection.should_close_with_result
    connection.should_close_with_result = False

    try:
        connection.scalar(select([1]))
    except exc.DBAPIError as err:
        if err.connection_invalidated:
            connection.scalar(select([1]))
        else:
            raise
    finally:
        connection.should_close_with_result = save_should_close_with_result


@contextlib.contextmanager
def transaction():
    try:
        session = ScopedSession()
        yield session
        session.commit()
    except:
        LOG.exception("Transaction failed! Rolling back...")
        session.rollback()
        raise


def teardown():
    ScopedSession.remove()


def can_connect():
    try:
        engine.connect()
        return True
    except Exception:
        return False


class MetaBase(declarative.DeclarativeMeta):
    def __init__(cls, klsname, bases, attrs):
        if klsname != "Base":
            super().__init__(klsname, bases, attrs)
            for attr_name, attr in attrs.items():
                if isinstance(attr, sa.Column):
                    query_single_getter_name = "get_by_{}".format(attr_name)
                    query_all_getter_name = "get_all_by_{}".format(attr_name)
                    if not hasattr(cls, query_single_getter_name):
                        setattr(cls, query_single_getter_name,
                                functools.partial(cls._get_by, attr))

                    if not hasattr(cls, query_all_getter_name):
                        setattr(cls, query_all_getter_name,
                                functools.partial(cls._get_all_by, attr))
                # TODO This does not work
                # if isinstance(attr, hybrid.hybrid_property):
                #    print(attr, type(attr))
                #    setattr(cls, "get_by_{}".format(attr_name),
                #          functools.partial(cls._get_by_property, attr))


class ModelBase(object):
    created_at = sa.Column(sa.DateTime(), server_default=func.now())
    updated_at = sa.Column(sa.DateTime(), onupdate=func.now())
    __table_args__ = TABLE_KWARGS

    @declarative.declared_attr
    def __tablename__(cls):  # pylint: disable=no-self-argument
        """ Returns a snake_case form of the table name. """
        return db_utils.pluralize(db_utils.to_snake_case(cls.__name__))

    def __eq__(self, other):
        if not other:
            return False
        return self.id == other.id

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        if hasattr(self, key):
            return setattr(self, key, value)
        raise AttributeError(key)

    def __contains__(self, key):
        return hasattr(self, key)

    def update(self, **fields):
        for attr, value in fields.items():
            if attr not in self:
                raise exception.ModelUnknownAttrbute(model=self, attr=attr)
            self[attr] = value
        return self

    @classmethod
    def get(cls, pk):
        return Session.query(cls).filter(cls.id == pk).first()

    @classmethod
    def _get_by_property(cls, prop):
        LOG.debug("Fetching '%s' by property '%s'", cls, prop)
        return Session.query(cls).filter(prop).first()

    @classmethod
    def _get_by(cls, field, value):
        LOG.debug("Fetching one '%s.%s' by value '%s'", cls, field, value)
        return Session.query(cls).filter(field == value).first()

    @classmethod
    def _get_all_by(cls, field, value):
        LOG.debug("Fetching all '%s.%s' with value '%s'", cls, field, value)
        return Session.query(cls).filter(field == value).all()

    @classmethod
    def last(cls):
        return Session.query(cls).order_by(cls.id.desc()).first()

    def save(self):
        LOG.debug("Attempting to save '%s'", self)
        with transaction() as session:
            session.add(self)

    def delete(self):
        LOG.debug("Attempting to delete '%s'", self)
        with transaction() as session:
            session.delete(self)

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items()
                if not callable(value) and not key.startswith('_')}


Base = declarative.declarative_base(cls=ModelBase, bind=engine,
                                    metaclass=MetaBase)


# pylint: disable=abstract-method,unused-argument
# TODO This parent class may not allow NULL to go into a UUID field :-|
class GUID(sqlalchemy_utils.UUIDType):
    """
    Overload of the sqlalchemy_utils UUID class. There are issues
    with it and alembic, acknowledged by the maintainer:
    https://github.com/kvesteri/sqlalchemy-utils/issues/129

    """
    def __init__(self, length=16, binary=True, native=True):
        # pylint: disable=unused-argument
        # NOTE(mdietz): Ignoring length, see:
        # https://github.com/kvesteri/sqlalchemy-utils/issues/129
        super(GUID, self).__init__(binary, native)


class HasId(object):
    """id mixin, add to subclasses that have an id."""

    id = sa.Column(GUID,
                   primary_key=True,
                   default=db_utils.generate_guid)


class ImageMixin(object):
    """image main_image mixin, add to subclasses that have images."""
    exclude = tuple(CONF.get('allowed.video.extensions').split(','))

    @property
    @abstractmethod
    def images(self):
        raise NotImplementedError

    @property
    def main_image(self):
        images = [Image()]
        if self.images:
            images = [image for image in self.images if not image.image_url.endswith(self.exclude)]
            if not images:
                images = [Image()]
        return images[-1]


class NotificationType(Base, HasId):
    description = sa.Column(sa.String(80), nullable=False)
    priority = sa.Column(sa.Integer(), nullable=True)
    notifications = orm.relationship("Notification", backref="type")

    def __str__(self):
        return self.description

    def __repr__(self):
        return "NotificationType:{}, {}".format(self.id, self.description)


class Notification(Base, HasId):
    notification_type_id = sa.Column(sa.ForeignKey("notification_types.id"),
                                     nullable=False)
    user_from_id = sa.Column(GUID(), sa.ForeignKey("users.id"), nullable=False)
    user_to_id = sa.Column(GUID(), sa.ForeignKey("users.id"), nullable=False)
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"), nullable=True)
    organization_id = sa.Column(GUID(), sa.ForeignKey("organizations.id"),
                                nullable=True)
    acknowledge_only = sa.Column(sa.Boolean(), nullable=False, default=False)
    blocked_as_spam = sa.Column(sa.Boolean(), nullable=False, default=False)
    accepted = sa.Column(sa.DateTime(), nullable=True, default=None)
    declined = sa.Column(sa.DateTime(), nullable=True, default=None)
    acknowledged = sa.Column(sa.DateTime(), nullable=True, default=None)

    @property
    def needs_action(self):
        return not self.acknowledge_only and not self.accepted and not self.declined

    def prevent_duplicate(self):
        user = User.get(self.user_to_id)
        notifications = user.group_notifications(self.group_id)
        for n in notifications:
            if (n.user_from_id == self.user_from_id and
                    n.notification_type_id == self.notification_type_id and
                    n.organization_id == self.organization_id):
                if n.blocked_as_spam:
                    return False
                self.accepted = None
                self.declined = None
                self.acknowledged = None
                elements = self.to_dict()
                updated_notification = n.update(**elements)
                return updated_notification
        return self


class OrganizationRole(Base, HasId):
    description = sa.Column(sa.String(120), nullable=False)
    priority = sa.Column(sa.Integer(), nullable=True)
    users = orm.relationship(
        "User", secondary='organization_members',
        back_populates="organization_roles")

    def __str__(self):
        return self.description

    def __repr__(self):
        return "OrganizationRole:{}, {}".format(self.id, self.description)


class User(Base, HasId, UserMixin, ImageMixin, renders.UserMixin):
    # TODO IMO these need to be contact details and a separate table
    first_name = sa.Column(sa.String(40), nullable=False)
    last_name = sa.Column(sa.String(40), nullable=False)
    # TODO Middle name?
    # TODO Title?
    # TODO Add a wholly separate ContactInfo table instead and one to
    # many from this?
    email = sa.Column(sa.String(254), nullable=False, unique=True)
    # http://stackoverflow.com/questions/3350500/international-phone-number-max-and-min
    phone_number = sa.Column(sa.String(16), nullable=True)
    hashed_password = sa.Column(sa.String(128), nullable=False)
    deleted_at = sa.Column(sa.DateTime(), nullable=True, default=None)
    zoom_user_id = sa.Column(sa.String(80), nullable=True)
    city = sa.Column(sa.String(80), nullable=True)
    date_of_birth = sa.Column(sa.Date(), nullable=True)
    super_admin = sa.Column(sa.Boolean(), nullable=False, default=False)
    images = orm.relationship('Image', secondary='user_images')
    privacy_and_terms_agreed_at = sa.Column(sa.DateTime(), nullable=True, default=None)
    # By name of zone rather than offset, which changes all the time
    timezone = sa.Column(sa.String(64), nullable=False)
    opt_in_texts = sa.Column(sa.Boolean(), nullable=False, default=False)
    opt_in_emails = sa.Column(sa.Boolean(), nullable=False, default=False)
    notifications_on = sa.Column(sa.Boolean(), nullable=False, default=True)
    # last_login = sa.Column(sa.DateTime(), server_default=func.now())
    verified_at = sa.Column(sa.DateTime(), nullable=True, default=None)

    organizations = orm.relationship(
        "Organization", secondary='organization_members',
        back_populates="users",
        primaryjoin=(
            'and_('
            'OrganizationMember.user_id==User.id, '
            'Organization.activated_at.isnot(None))'))

    groups = orm.relationship(
        "Group",
        secondary='group_members',
        back_populates="users",
        primaryjoin=(
            'and_('
            'GroupMember.user_id==User.id, '
            'GroupMember.group_id==Group.id, '
            'OrganizationGroup.group_id==Group.id, '
            'OrganizationGroup.organization_id==Organization.id, '
            'Organization.activated_at.isnot(None), '
            'Group.archived_at==None)'))

    organization_roles = orm.relationship(
        "OrganizationRole", secondary='organization_members',
        back_populates="users")

    group_roles = orm.relationship(
        "GroupRole", secondary='group_members',
        back_populates="users")

    notifications = orm.relationship(
        "Notification",
        foreign_keys="[Notification.user_to_id]",
        backref="to_user")

    sent_notifications = orm.relationship(
        "Notification",
        foreign_keys="[Notification.user_from_id]",
        backref="from_user")

    group_members = orm.relationship(
        "GroupMember",
        back_populates="users")

    organization_members = orm.relationship(
        "OrganizationMember",
        back_populates="users")

    group_leaders = orm.relationship(
        'Group',
        secondary='group_members',
        back_populates='users',
        primaryjoin=(
            "and_("
            "GroupMember.user_id==User.id, "
            "GroupMember.group_id==Group.id, "
            "GroupMember.role_id==GroupRole.id, "
            "OrganizationGroup.group_id==Group.id, "
            "OrganizationGroup.organization_id==Organization.id, "
            "GroupRole.description=='Group Leader')"))

    def __str__(self):
        return self.full_name_and_email

    def __repr__(self):
        return "User: {}, {}".format(self.id, self.full_name_and_email)

    def organizations_created(self):
        # TODO: Refactor.
        # I think we should add Group.parent_org and Org.creator columns
        # to avoid this huge db query
        subquery = Session.query(func.min(
            OrganizationMember.created_at).label('created_at')).group_by(
                OrganizationMember.organization_id).subquery()
        query = Session.query(Organization).join(
            OrganizationMember, OrganizationRole, User).join(
                subquery,
                subquery.c.created_at == OrganizationMember.created_at).filter(
                    Organization.activated_at.isnot(None),
                    OrganizationRole.description == 'Owner',
                    User.email == self.email)
        return query.all()

    @property
    def new_notifications(self):
        return [n for n in self.notifications if
                not n.acknowledged]

    @property
    def non_acknowledged_notifications(self):
        return [n for n in self.sent_notifications if
                not n.acknowledged and (n.accepted or n.declined)]

    @property
    def get_notifications(self):
        return (self.new_notifications +
                self.non_acknowledged_notifications)

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def short_name(self):
        return "{} {}.".format(self.first_name, self.last_name[:1])

    @property
    def full_name_and_email(self):
        return "{} ({})".format(self.full_name, self.email)

    def group_notifications(self, group_id):
        return (n for n in self.notifications if
                n.group_id == group_id)

    def org_notifications(self, org_id):
        return (n for n in self.notifications if
                n.org_id is org_id)

    # NOTE: this fails as soon as we allow a user to have more than one
    # role in an organization
    def role_for_org(self, org_id):
        roles = [om.role for om in self.organization_members
                 if om.organization.id == org_id]
        return roles[0] if roles else None

    # NOTE: this fails as soon as we allow a user to have more than one
    # role in an group
    def role_for_group(self, group_id):
        roles = [gm.role for gm in self.group_members
                 if gm.group and gm.group.id == group_id]
        return roles[0] if roles else None

    def is_group_member(self, group_id):
        return group_id in [g.id for g in self.groups]

    def is_org_creator(self, org_id):
        organization = Organization.get(org_id)
        return organization.creator.id == self.id

    def is_org_owner(self, org_id=None):
        if not org_id:
            return 'Owner' in [g.description for g in
                               self.organization_roles]
        return any([om for om in self.organization_members if
                    om.organization_id == org_id and
                    om.role.description == 'Owner'])

    def can_view_group_items(self, group_id):
        g = Group.get(group_id)
        return (self.super_admin or
                self.is_group_member(group_id) or
                self.is_group_admin(g.parent_org.id))

    def is_org_admin(self, org_id=None):
        if not org_id:
            return 'Organization Administrator' in [g.description for g in
                                                    self.organization_roles]
        return any([om for om in self.organization_members if
                    om.organization_id == org_id and
                    om.role.description == 'Organization Administrator'])

    def is_org_member(self, org_id):
        return any([om for om in self.organization_members if
                    om.organization_id == org_id and
                    om.role.description == 'Member'])

    def is_in_org(self, org_id):
        return org_id in [g.id for g in self.organizations]

    def is_group_leader(self, group_id):
        return any([gm for gm in self.group_members if
                    gm.group_id == group_id and
                    gm.role.description == 'Group Leader'])

    def is_meeting_alternate_host(self, group_id):
        return any([gm for gm in self.group_members if
                    gm.can_cohost_meeting == 1])

    def is_group_admin(self, org_id=None):
        if not org_id:
            return 'Group Administrator' in [g.description for g in
                                             self.organization_roles]

        return any([om for om in self.organization_members if
                    om.organization_id == org_id and
                    om.role.description == 'Group Administrator'])

    def is_group_creator(self, org_id=None):
        if not org_id:
            return 'Group Creator' in [g.description for g in
                                       self.organization_roles]
        return any([om for om in self.organization_members if
                    om.organization_id == org_id and
                    om.role.description == 'Group Creator'])

    def can_add_group(self, group_id=None, org_id=None):
        return (self.super_admin or
                self.is_org_owner(org_id) or
                self.is_org_admin(org_id) or
                self.is_group_admin(org_id) or
                self.is_group_creator(org_id))

    def can_edit_group(self, group_id=None):
        group = Group.get(group_id)
        org_id = group.parent_org.id
        return (self.super_admin or
                self.is_group_leader(group.id) or
                self.is_group_admin(org_id) or
                self.can_edit_org(org_id))

    def can_change_group_members_role(self, group):
        org_id = group.parent_org.id
        return (self.super_admin or
                self.is_group_admin(org_id) or
                self.can_edit_org(org_id))

    def can_edit_org(self, org_id):
        return (self.super_admin or
                self.is_org_owner(org_id) or
                self.is_org_admin(org_id))

    def can_manage_subscription(self, org_id):
        return any([om for om in self.organization_members if
                    om.organization_id == org_id and
                    om.can_manage_subscription])

    @classmethod
    def get_email_from_full_name_and_email(cls, full_name_and_email):
        regex = r"(\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*)"
        matches = re.findall(regex, full_name_and_email)
        if not matches:
            raise exception.InvalidEmail()
        return matches[0][0]


class LinkType(Base, HasId):
    description = sa.Column(sa.String(200), nullable=False)
    priority = sa.Column(sa.Integer(), nullable=True)
    link = orm.relationship('Link', backref='link_type')

    @property
    def icon(self):
        return '-'.join(self.description.lower().split(' '))

    def __str__(self):
        return self.description

    def __repr__(self):
        return "LinkType:{}, {}".format(self.id, self.description)


class Link(Base, HasId):
    link_type_id = sa.Column(GUID(), sa.ForeignKey("link_types.id"))
    icon_css_class = sa.Column(sa.String(120))
    organization_id = sa.Column(GUID(), sa.ForeignKey("organizations.id"), nullable=True)
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"), nullable=True)
    url = sa.Column(sa.String(250), nullable=False)

    @property
    def formatted_url(self):
        if 'http' in self.url:
            return self.url
        return "http://{}".format(self.url)


class Address(Base, HasId):
    # TODO I think this is the correct mapping
    # organization_id = sa.Column(GUID(), sa.ForeignKey("organization.id"))
    # organization = orm.relationship("Organization", backref="addresses")
    # TODO Nothing International?
    # TODO this needs to be split up into street number and street IMO
    street_address = sa.Column(sa.String(100), nullable=False)
    city = sa.Column(sa.String(100), nullable=False)
    # TODO this should be an enum
    state = sa.Column(sa.String(30), nullable=False)
    # TODO No country?
    zip_code = sa.Column(sa.String(9), nullable=True)
    organization = orm.relationship('Organization', backref='address')

    @property
    def formatted(self):
        return "{} {}, {} {}".format(self.street_address,
                                     self.city,
                                     self.state,
                                     self.zip_code)

    @property
    def line1(self):
        return "{}".format(self.street_address)

    @property
    def line2(self):
        return "{}, {} {}".format(self.city,
                                  self.state,
                                  self.zip_code)

    def __str__(self):
        return self.formatted

    def __repr__(self):
        return "Address:{}, {}".format(self.id, self.formatted)


class ZoomMeeting(Base, HasId, renders.MeetingMixin):
    # https://zoom.us/
    # TODO Is this the only type they want to support?
    # TODO This seems insufficient. Probably need Outlook-meeting-like
    #     granularity
    SCHEDULED_MEETING = 2
    REPEATED_MEETING = 3
    DEFAULT_MEETING_LENGTH = 60
    LIST_LIMIT = int(CONF.get('zoom.meeting.list.limit', 30))
    meeting_id = sa.Column(sa.String(255), nullable=False)
    duration = sa.Column(sa.Integer(), nullable=False, default=60)
    meeting_start = sa.Column(sa.DateTime(), nullable=False, default=None)
    # TODO model this as an enumerable type?
    repeat_type = sa.Column(sa.String(10))
    topic = sa.Column(sa.String(100), nullable=False)
    start_url = sa.Column(sa.String(500), nullable=False)
    join_url = sa.Column(sa.String(255), nullable=False)
    repeat_end_date = sa.Column(sa.Date(), nullable=True, default=None)
    user_id = sa.Column(GUID(), sa.ForeignKey("users.id"), nullable=False)
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"))

    def url(self, user_id):
        if self.can_host_meeting(user_id):
            return self.start_url
        return self.join_url

    def can_host_meeting(self, user_id):
        u = User.get(user_id)
        return self.user_id == user_id or u.is_meeting_alternate_host(
            self.group_id)

    def info(self, timezone):
        if self.repeat_type == str(self.REPEATED_MEETING):
            output = "Every {} at {}".format(
                helper.day_of_week(self.meeting_start, timezone),
                helper.time_only_offset(self.meeting_start, timezone))
            if self.repeat_end_date:
                output += "<br/>{}-{}".format(
                    self.start_date_with_timezone(timezone),
                    self.repeat_end_date.strftime(constants.DATE_FORMAT))
            return output
        if self.single_day_event:
            return "{} - {}".format(
                self.start_with_timezone(timezone),
                self.end_time_with_timezone(timezone))
        return  "{} - {}".format(
            self.start_with_timezone(timezone),
            self.end_with_timezone(timezone))

    @property
    def single_day_event(self):
        if self.start_date == self.end_date:
            return True
        return False

    @property
    def duration_time(self):
        return helper.seconds_to_hours_and_minutes(self.duration)

    @property
    def start_time(self):
        return helper.time_only_offset(self.meeting_start)

    @property
    def start_date(self):
        return helper.date_only_offset(self.meeting_start)

    @property
    def end_time(self):
        return helper.time_only_offset(self.meeting_end)

    @property
    def end_date(self):
        return helper.date_only_offset(self.meeting_end)

    @property
    def meeting_end(self):
        return self.meeting_start + datetime.timedelta(minutes=self.duration)

    def start_with_timezone(self, timezone):
        return helper.datetime_offset(self.meeting_start, timezone)

    def end_with_timezone(self, timezone):
        return helper.datetime_offset(self.meeting_end, timezone)

    def start_time_with_timezone(self, timezone):
        return helper.time_only_offset(self.meeting_start, timezone)

    def end_time_with_timezone(self, timezone):
        return helper.time_only_offset(self.meeting_end, timezone)

    def start_date_with_timezone(self, timezone):
        return helper.date_only_offset(self.meeting_start, timezone)

    def end_date_with_timezone(self, timezone):
        return helper.date_only_offset(self.meeting_end, timezone)


class GroupMember(Base, HasId):
    __table_args__ = (sa.UniqueConstraint("group_id", "user_id",
                                          name="group_user_membership"),
                      TABLE_KWARGS)
    # join table for groups and users
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"))
    user_id = sa.Column(GUID(), sa.ForeignKey("users.id"))
    role_id = sa.Column(GUID(), sa.ForeignKey("group_roles.id"))
    can_cohost_meeting = sa.Column(sa.Boolean(), nullable=False, default=False)
    # TODO IMO we don't keep deleted_at OR we keep *all* of them on all models
    deleted_at = sa.Column(sa.DateTime(), nullable=True, default=None)
    user = orm.relationship('User')
    group = orm.relationship('Group')
    role = orm.relationship('GroupRole')
    users = orm.relationship(
        "User",
        back_populates="group_members")


# TODO If these represent permissions, we can probably do this better, globally
class GroupRole(Base, HasId):
    description = sa.Column(sa.String(80), nullable=False)
    priority = sa.Column(sa.Integer(), nullable=True)
    users = orm.relationship(
        "User", secondary='group_members',
        back_populates="group_roles")

    def __str__(self):
        return self.description

    def __repr__(self):
        return "GroupRole:{}, {}".format(id, self.description)


class GroupDocument(Base, HasId, renders.GroupDocumentMixin):
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"))
    friendly_name = sa.Column(sa.String(80), nullable=False)
    file_url = sa.Column(sa.String(250), nullable=True)


class AgeRange(Base, HasId):
    description = sa.Column(sa.String(80))
    priority = sa.Column(sa.Integer(), nullable=True)
    groups = orm.relationship('Group', backref='age_range')

    def __str__(self):
        return self.description

    def __repr__(self):
        return "AgeRange:{}, {}".format(id, self.description)


class GroupMeetTime(Base, HasId):
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"))
    meet_time_type_id = sa.Column(GUID(), sa.ForeignKey("meet_time_types.id"))

    def __str__(self):
        return "GroupMeetTime group_id: {}, meet_time_type_id: {}".format(
            self.group_id, self.meet_time_type_id)

    def __repr__(self):
        return "GroupMeetTime:{}, group_id: {}, meet_time_type_id: {}".format(
            self.id, self.group_id, self.meet_time_type_id)

    def __hash__(self):
        return hash(str(self))


class MeetTimeType(Base, HasId):
    description = sa.Column(sa.String(80), nullable=False)
    group_meet_time = orm.relationship('GroupMeetTime',
                                       backref='meet_time_type')
    priority = sa.Column(sa.Integer(), nullable=True)

    def __str__(self):
        return self.description

    def __repr__(self):
        return "MeetTimeType:{}, {}".format(self.id, self.description)


class GroupType(Base, HasId):
    description = sa.Column(sa.String(80), nullable=False)
    priority = sa.Column(sa.Integer(), nullable=True)
    # Has a one to many relationship to Groups, but Why? maybe backref?
    groups = orm.relationship('Group', backref='group_type')

    def __str__(self):
        return self.description

    def __repr__(self):
        return "GroupType:{}, {}".format(self.id, self.description)


class GroupPrivacySetting(Base, HasId):
    priority = sa.Column(sa.Integer(), nullable=True)
    description = sa.Column(sa.String(80), nullable=False)
    # has a one to many relationship to Groups, by Why? maybe backref?

    @hybrid.hybrid_property
    def is_public(self):
        return self.description.startswith("Public")

    @hybrid.hybrid_property
    def is_org_only(self):
        return self.description.startswith("Organization Only")

    def __str__(self):
        return self.description

    def __repr__(self):
        return "GroupPrivacySetting:{}, {}".format(self.id, self.description)


class OrganizationGroup(Base, HasId):
    organization_id = sa.Column(GUID(), sa.ForeignKey("organizations.id"))
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"))
    order = sa.Column(sa.Integer(), default=0)

    organization = orm.relationship('Organization')
    group = orm.relationship('Group')


class Group(Base, HasId, ImageMixin, renders.GroupMixin):
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text(), nullable=False)
    member_limit = sa.Column(sa.Text(), nullable=True)
    archived_at = sa.Column(sa.DateTime(), nullable=True, default=None)
    tag_line = sa.Column(sa.String(80), nullable=True)
    # TODO This is racey and requires locking
    clicks = sa.Column(sa.Integer(), nullable=False, default=0)
    age_range_id = sa.Column(GUID(), sa.ForeignKey("age_ranges.id"),
                             nullable=True)
    anonymous = sa.Column(sa.Boolean(), nullable=False, default=False)
    # NOTE For now, this will be M, F, and None, and should be an FK to
    # an enum table
    gender_focus = sa.Column(sa.String(80), nullable=True)
    images = orm.relationship('Image', secondary='group_images')
    privacy_setting_id = sa.Column(
        GUID(), sa.ForeignKey("group_privacy_settings.id"))
    privacy_settings = orm.relationship("GroupPrivacySetting",
                                        backref="group")
    group_type_id = sa.Column(GUID(), sa.ForeignKey("group_types.id"),
                              nullable=True)
    organizations = orm.relationship('Organization',
                                     secondary='organization_groups',
                                     back_populates='groups')
    documents = orm.relationship('GroupDocument',
                                 backref='group')
    meet_times = orm.relationship('GroupMeetTime', backref='group')
    meetings = orm.relationship('ZoomMeeting',
                                backref='group')
    users = orm.relationship('User',
                             secondary='group_members',
                             back_populates='groups')
    gender_translation = {'M': "Men's Group",
                          'F': "Women's Group",
                          None: 'Men and Women',
                          '': 'Men and Women'}
    notifications = orm.relationship("Notification", backref="group")
    leaders = orm.relationship('User',
                               secondary='group_members',
                               back_populates='groups',
                               primaryjoin=(
                                   "and_("
                                   "GroupMember.user_id==User.id, "
                                   "GroupMember.group_id==Group.id, "
                                   "GroupMember.role_id==GroupRole.id, "
                                   "GroupRole.description=='Group Leader')"))
    links = orm.relationship('Link', backref='group')

    @property
    def parent_org(self):
        return self.organizations[0]

    @property
    def org_creator(self):
        org = Organization.get(self.parent_org.id)
        return org.creator

    @property
    def is_payed_up(self):
        org = Organization.get(self.parent_org.id)
        return org.is_payed_up

    def is_joinable(self):
        if not self.member_limit:
            return True
        return self.member_limit > len(self.users)

    @property
    def get_meet_times(self):
        ids = []
        for meet_time in self.meet_times:
            if meet_time.meet_time_type_id:
                ids.append(meet_time.meet_time_type_id)
        meet_descriptions = []
        if ids:
            with transaction() as session:
                meet_types = (session.query(MeetTimeType)
                              .filter(MeetTimeType.id.in_(ids))
                              .options(orm.load_only('description'))
                              .all())
                meet_descriptions = [meet_type.description for meet_type in meet_types]
        return meet_descriptions

    @property
    def gender_focus_formatted(self):
        return self.gender_translation.get(self.gender_focus, None)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Group:{}, {}".format(self.id, self.name)


class Organization(Base, HasId, ImageMixin, renders.OrganizationMixin):
    # TODO We should talk to Toneo about allowing people to craft this
    #     model piecemeal, but only allow them to "publish" their Org
    #     after all the minimum detail is met. This also could use
    #     some vetting/approval process
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text(), nullable=True, default=None)
    deleted_at = sa.Column(sa.DateTime(), nullable=True, default=None)
    show_address = sa.Column(sa.Boolean(), nullable=False, default=True)

    vanity_name = sa.Column(sa.String(80), nullable=True, default=None)
    # TODO This is very clearly church focused. What should we do with this?
    #     and how should we migrate it?
    service_times_description = sa.Column(sa.String(80), nullable=True,
                                          default=None)
    date_established = sa.Column(sa.DateTime(), nullable=True)
    address_id = sa.Column(GUID(), sa.ForeignKey("addresses.id"))

    users = orm.relationship('User',
                             secondary='organization_members',
                             back_populates='organizations',
                             order_by='OrganizationMember.created_at')

    owners = orm.relationship('OrganizationMember',
                              secondary='organization_roles',
                              primaryjoin=(
                                  'and_('
                                  'OrganizationMember.organization_id=='
                                  'Organization.id, '
                                  'OrganizationRole.description=="Owner")'),
                              order_by='OrganizationMember.created_at')

    links = orm.relationship('Link', backref='organization')
    # The primaryjoin here excludes archived groups
    groups = orm.relationship('Group',
                              secondary='organization_groups',
                              back_populates='organizations',
                              order_by='OrganizationGroup.order',
                              primaryjoin=(
                                  'and_('
                                  'OrganizationGroup.organization_id=='
                                  'Organization.id, '
                                  'OrganizationGroup.group_id==Group.id, '
                                  'Organization.activated_at.isnot(None), '
                                  'Group.archived_at==None)'))
    group_leaders = orm.relationship(
        'User',
        secondary='group_members',
        back_populates='organizations',
        primaryjoin=('and_('
                     'GroupMember.user_id==User.id, '
                     'GroupMember.group_id==Group.id, '
                     'GroupMember.role_id==GroupRole.id, '
                     'OrganizationGroup.group_id==Group.id, '
                     'OrganizationGroup.organization_id==Organization.id, '
                     'GroupRole.description=="Group Leader", '
                     'Group.archived_at==None)'))
    images = orm.relationship('Image', secondary='organization_images')
    notifications = orm.relationship('Notification', backref='organization')
    activated_at = sa.Column(sa.DateTime(), nullable=True, default=None)

    # Cache elements
    licenses = 0
    allocated_licenses = 0
    billing_date = False
    sub_data = None
    discount_data = 0

    @property
    def group_leader_count(self):
        # TODO: Flag the correct organization as is_lifeloop, refer to that
        # TODO: Add 'no_charge' flag to organizations who we don't bill
        llw_org = Organization.get(CONF.get("llw.org.id"))
        llw_leaders = llw_org.group_leaders
        count = 0
        for leader in self.group_leaders:
            if leader not in llw_leaders:
                count += 1
        return count

    @property
    def purchased_licenses(self):
        if not self.allocated_licenses and self.subscription_data:
            subscription_driver = subscription.ChargifyDriver(self.id)
            allocation = (
                subscription_driver.
                get_subscription_component_allocation(
                    self.subscription_data['id']))
            self.allocated_licenses = allocation['quantity']
        return self.allocated_licenses

    @property
    def available_licenses(self):
        if not self.licenses:
            purchased = self.purchased_licenses + 1 # base license
            used = self.group_leader_count
            total = purchased - used
            self.licenses = 0 if total < 0 else total
        return self.licenses

    def next_billing_date(self):
        if not self.billing_date:
            if self.subscription_data:
                data = self.subscription_data['current_period_ends_at']
                date = data[0:19]
                date_time = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
                self.billing_date = helper.datetime_offset(
                    date_time, self.timezone)
        return self.billing_date

    @property
    def cancel_at_end_of_period(self):
        if self.subscription_data:
            return self.subscription_data['cancel_at_end_of_period']
        return False

    def is_in_trial(self):
        date = self.next_billing_date()
        if date:
            datetime_now = datetime.datetime.utcnow()
            now = helper.datetime_offset(datetime_now, self.timezone)
            if now < date:
                return True
        return False

    @property
    def subscription_data(self):
        if not self.sub_data:
            subscription_driver = subscription.ChargifyDriver(self.id)
            self.sub_data = subscription_driver.get_subscription(self.id)
        return self.sub_data

    @property
    def coupon(self):
        LOG.debug(self.subscription_data)
        if 'coupon_code' in self.subscription_data:
            return self.subscription_data['coupon_code']
        return None

    @property
    def discount(self):
        if self.coupon and not self.discount_data:
            subscription_driver = subscription.subscription_driver()
            self.discount_data = subscription_driver.get_discount(self.coupon)
        return self.discount_data

    @property
    def is_active(self):
        return self.activated_at is not None

    @property
    def is_payed_up(self):
        if self.subscription_data and self.available_licenses >= 0:
            return True
        return self.is_in_trial()

    @property
    def creator(self):
        owners = self.owners
        return (owners[0].user if len(owners) == 1 else
                [om for om in owners if om.user.email.find("lifeloop.live") < 0][0].user)

    @property
    def timezone(self):
        return self.creator.timezone

    def public_groups(self):
        return [g for g in self.groups
                if g.privacy_settings.description.lower()
                .startswith('public')]

    def private_groups(self):
        return [g for g in self.groups
                if g.privacy_settings.description.lower()
                .startswith('private')]

    def org_only_groups(self):
        return [g for g in self.groups
                if g.privacy_settings.description.lower()
                .startswith('organization only')]

    def public_and_org_only_groups(self):
        return [g for g in self.groups
                if g.privacy_settings.description.lower()
                .startswith('organization only') or g.privacy_settings
                .description.lower().startswith('public')]

    @property
    def website(self):
        for link in self.links:
            if link.link_type.description.split(' ')[-1] == 'Website':
                return link.url
        return None

    def __repr__(self):
        return "Organization: {}, name: {}".format(
            self.id, self.name)

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other):
        return self.name < other.name


class OrganizationMember(Base, HasId):
    __table_args__ = (sa.UniqueConstraint("organization_id", "user_id",
                                          name="org_user_membership"),
                      TABLE_KWARGS)
    user_id = sa.Column(GUID(), sa.ForeignKey("users.id"))
    organization_id = sa.Column(GUID(), sa.ForeignKey("organizations.id"), index=True)
    # TODO Should be many?
    role_id = sa.Column(GUID(), sa.ForeignKey("organization_roles.id"))
    user = orm.relationship('User')
    organization = orm.relationship('Organization')
    role = orm.relationship('OrganizationRole')
    can_manage_subscription = sa.Column(sa.Boolean(), nullable=False, default=False)
    users = orm.relationship(
        "User",
        back_populates="organization_members")

    def __str__(self):
        return self.user.full_name

    def __repr__(self):
        return "OrganizationMember:{}, {}".format(self.id, self.user.full_name)


class UserImage(Base, HasId):
    user_id = sa.Column(GUID(), sa.ForeignKey("users.id"))
    image_id = sa.Column(GUID(), sa.ForeignKey("images.id"))
    user = orm.relationship('User')
    image = orm.relationship('Image')


class GroupImage(Base, HasId):
    group_id = sa.Column(GUID(), sa.ForeignKey("groups.id"))
    image_id = sa.Column(GUID(), sa.ForeignKey("images.id"))
    group = orm.relationship('Group')
    image = orm.relationship('Image')


class OrganizationImage(Base, HasId):
    organization_id = sa.Column(GUID(), sa.ForeignKey("organizations.id"))
    image_id = sa.Column(GUID(), sa.ForeignKey("images.id"))
    organization = orm.relationship('Organization')
    image = orm.relationship('Image')


class Image(Base, HasId):
    image_url = sa.Column(sa.String(500), nullable=False)
    public_id = sa.Column(sa.String(255), nullable=True)
    # NOTE: TEMPORARY WHILE MIGRATING TO JOIN TABLES
    organization_id = sa.Column(GUID(), nullable=True)

    @property
    def url(self):
        if self.image_url:
            return self.image_url
        return webpack.asset_url_for('images/card.default.png')

class Page(Base, HasId):
    title = sa.Column(sa.String(60), nullable=False)
    content = sa.Column(sa.String(20000), nullable=False)
    pagetype = sa.Column(sa.Integer(), nullable=False)
    updated_by = sa.Column(sa.String(60), nullable=False)
