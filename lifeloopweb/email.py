import os
import smtplib
import socket

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import flask
import jinja2
import requests
from lifeloopweb import config, exception, logging, token, webpack
from lifeloopweb.helpers.base_helper import Helper

EMAIL_DRIVER = None
CONF = config.CONF
LOG = logging.get_logger(__name__)
DOMAIN = CONF.get("site.domain")

helper = Helper()


class EmailDriver(object):
    def send_mail(self, **mail):
        raise NotImplementedError("Parent EmailDriver has no implementation")


class MailgunDriver(EmailDriver):
    REQUEST_URL = 'https://api.mailgun.net/v3/{}/messages'

    def __init__(self):
        self._key = CONF.get("mailgun.api.key")
        self._domain = CONF.get("mailgun.domain")
        LOG.debug("Initializing MailgunDriver")
        LOG.debug("Mailgun domain: %s", self._domain)
        super().__init__()

    def _endpoint_url(self):
        return self.REQUEST_URL.format(self._domain)

    def send_mail(self, **mail):
        from_email = mail.get('from', CONF.get("email.mailfrom"))
        LOG.debug(
            "Sending mailgun email from '%s' to '%s'", from_email, mail["to"])
        request = requests.post(
            self._endpoint_url(), auth=('api', self._key),
            data={'from': from_email, 'to': mail['to'],
                  'subject': mail['subject'], 'html': mail['text']})
        return request.status_code == 200


class SendmailDriver(EmailDriver):
    """ SendmailDriver
    Used to send emails for testing. Expects multiple environment variables
    to be set and is used for testing, not production."""

    def __init__(self):
        if CONF.get("production"):
            raise exception.InvalidProductionConfig(
                msg="SendmailDriver is forbidden in production")

        LOG.debug("Initializing SendmailDriver")
        self._host = CONF.get("email.host")
        self._port = int(CONF.get("email.port"))
        self._email_address = CONF.get("support.email.address")
        # TODO This should probably be in the global config
        self._hostname = socket.gethostname()
        super().__init__()

    def send_mail(self, **mail):
        mail_to = mail["to"]
        msg = MIMEMultipart()
        msg['Subject'] = mail['subject']
        msg['From'] = self._email_address
        msg['To'] = mail['to']
        html = mail['text']
        part = MIMEText(html, 'html')
        msg.attach(part)

        srv = smtplib.SMTP(self._host, self._port)

        LOG.debug("Sendmail host: %s", self._host)
        LOG.debug("Sendmail port: %s", self._port)
        LOG.debug("Sendmail recipient email: %s", self._email_address)
        LOG.debug("msg: %s", msg)
        srv.sendmail(
            from_addr=self._email_address,
            to_addrs=[mail_to],
            msg=msg.as_string())
        srv.close()
        return True


class LifeloopEmail(object):
    def __init__(self):
        # TODO We might want to support multiple Loaders here.
        self._template_engine = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                os.path.realpath(CONF.get("email.templates.folder"))),
            autoescape=jinja2.select_autoescape(["html"]))
        self._driver = EMAIL_DRIVER
        self._tmpl = self._template_engine.get_template(self.TEMPLATE)

    def send(self, mail_from, mail_to, **kwargs):
        raise NotImplementedError(
            "Base class LifeloopEmail does not support sending")

    def _send(self, mail_from, mail_to, **kwargs):
        items = {**self.base_template_kwargs(), **kwargs}
        if kwargs.get("subject"):
            subject = kwargs["subject"]
        else:
            subject = self.SUBJECT
        mail = {
            "to": mail_to,
            "from": mail_from,
            "subject": subject,
            "text": self._tmpl.render(**items)}
        self._driver.send_mail(**mail)

    @staticmethod
    def base_template_kwargs():
        return {
            'faq_url': "{}{}".format(DOMAIN, flask.url_for('faq')),
            'index_url': "{}{}".format(DOMAIN, flask.url_for('index')),
            'contact_url': "{}{}".format(DOMAIN, flask.url_for('contact')),
            'privacy_url': "{}{}".format(DOMAIN, flask.url_for('privacy')),
            'terms_url': "{}{}".format(DOMAIN, flask.url_for('terms')),
            'header_image_url': "{}{}".format(DOMAIN, webpack.webpack.asset_url_for(
                'images/logo/logo-w.png')),
            'facebook_image_url': "{}{}".format(DOMAIN, webpack.webpack.asset_url_for(
                'images/email/facebook.png')),
            'twitter_image_url': "{}{}".format(DOMAIN, webpack.webpack.asset_url_for(
                'images/email/twitter.png')),
            'pinterest_image_url': "{}{}".format(DOMAIN, webpack.webpack.asset_url_for(
                'images/email/pinterest.png')),
            'youtube_image_url': "{}{}".format(DOMAIN, webpack.webpack.asset_url_for(
                'images/email/youtube.png'))}


class TokenEmail(LifeloopEmail):
    def decrypt_token(self, password_token):
        return token.decrypt(password_token, self.SALT, self.EXPIRY)

    def send(self, mail_from, mail_to, **kwargs):
        return_route = kwargs["return_route"]
        content = {'mail_to': mail_to}
        new_token = token.create(content, self.SALT, self.EXPIRY)
        token_url = "{}/{}/{}".format(DOMAIN, return_route, str(new_token))
        self._send(mail_from, mail_to, token_url=token_url)


class RegistrationEmail(TokenEmail):
    TEMPLATE = "register.html"
    SALT = "lifeloop-registration-email"
    EXPIRY = helper.days(int(CONF.get("token.expires.in.days")))
    SUBJECT = "LifeLoop.Live User Registration"


class ForgotPasswordEmail(TokenEmail):
    TEMPLATE = "forgot_password.html"
    SALT = "lifeloop-forgot-password-email"
    EXPIRY = helper.days(int(CONF.get("token.expires.in.hours")))
    SUBJECT = "LifeLoop.Live Reset Password"


class InviteNewMemberEmail(LifeloopEmail):
    SALT = "lifeloop-invite-member-email"
    EXPIRY = helper.days(int(CONF.get("token.expires.in.days")))
    SUBJECT = "LifeLoop.Live Invitation"

    def send(self, mail_from, mail_to, **kwargs):
        raise NotImplementedError(
            "InviteNewMemberEmail has no send implementation")


class OrgInviteNewMemberEmail(InviteNewMemberEmail):
    TEMPLATE = "org_invite.html"

    def send(self, mail_from, mail_to, **kwargs):
        org = kwargs.get("org")
        role = kwargs.get("role")
        content = {'mail_to': mail_to, 'org_id': str(org.id),
                   'org_role_id': str(role.id)}
        invite_token = token.create(content, self.SALT, self.EXPIRY)
        register_url = "{}{}".format(
            DOMAIN, flask.url_for(
                'orgs.register_user_by_invite_create',
                token=str(invite_token)))
        self._send(
            mail_from,
            mail_to,
            org=org,
            role=role,
            register_url=register_url)

    def decrypt_token(self, invite_token):
        return token.decrypt(invite_token, self.SALT, self.EXPIRY)


class GroupInviteNewMemberEmail(InviteNewMemberEmail):
    TEMPLATE = "group_invite.html"

    def send(self, mail_from, mail_to, **kwargs):
        group = kwargs.get("group")
        role = kwargs.get("role")
        content = {'mail_to': mail_to, 'group_id': str(group.id),
                   'group_role_id': str(role.id)}
        invite_token = token.create(content, self.SALT, self.EXPIRY)
        register_url = "{}{}".format(
            DOMAIN, flask.url_for(
                'groups.register_user_by_invite_create',
                token=str(invite_token)))
        LOG.debug(
            "Sending a new member invitation email from '%s' to '%s'"
            " expiring in %s days", mail_from, mail_to, self.EXPIRY)
        self._send(
            mail_from,
            mail_to,
            group=group,
            register_url=register_url)

    def decrypt_token(self, invite_token):
        return token.decrypt(invite_token, self.SALT, self.EXPIRY)


class InviteExistingUserToGroupEmail(LifeloopEmail):
    TEMPLATE = "invite_existing_user_to_group.html"
    SUBJECT = "LifeLoop.Live Invitation to Join Group"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug(
            "Sending a new group member invitation email from '%s' to '%s'",
            mail_from, mail_to)
        group = kwargs.get("group")
        reminder = kwargs.get("reminder")
        if not group:
            raise exception.GroupNotFound()
        login_url = "{}{}".format(DOMAIN, flask.url_for('login'))
        self._send(
            mail_from,
            mail_to,
            group=group,
            login_url=login_url,
            reminder=reminder)


class OrgCreationRequestEmail(LifeloopEmail):
    TEMPLATE = "org_creation_request.html"
    SUBJECT = "LifeLoop.Live Organization Creation Request"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending an org creation request email from '%s' to '%s'",
                  mail_from, mail_to)
        org = kwargs.get("org")
        reminder = kwargs.get("reminder")
        if not org:
            raise exception.OrganizationNotFound()
        self._send(
            mail_from,
            mail_to,
            org=org,
            email=mail_from,
            reminder=reminder)


class InviteExistingUserToOrgEmail(LifeloopEmail):
    TEMPLATE = "invite_existing_user_to_org.html"
    SUBJECT = "LifeLoop.Live Invitation to Join Organization"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug(
            "Sending a new org member invitation email from '%s' to '%s'",
            mail_from, mail_to)
        org = kwargs.get("org")
        reminder = kwargs.get("reminder")
        if not org:
            raise exception.OrganizationNotFound()
        login_url = "{}{}".format(DOMAIN, flask.url_for('login'))
        self._send(
            mail_from,
            mail_to,
            org=org,
            login_url=login_url,
            reminder=reminder)


class GroupJoinRequestEmail(LifeloopEmail):
    TEMPLATE = "group_join_request.html"
    SUBJECT = "LifeLoop.Live Request to Join Group"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a new group join request email from '%s' to '%s'",
                  mail_from, mail_to)
        group = kwargs.get("group")
        reminder = kwargs.get("reminder")
        if not group:
            raise exception.GroupNotFound()
        self._send(
            mail_from,
            mail_to,
            group=group,
            email=mail_from,
            reminder=reminder)


class OrgJoinRequestEmail(LifeloopEmail):
    TEMPLATE = "org_join_request.html"
    SUBJECT = "LifeLoop.Live Request to Join Organization"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a new org join request email from '%s' to '%s'",
                  mail_from, mail_to)
        org = kwargs.get("org")
        reminder = kwargs.get("reminder")
        if not org:
            raise exception.OrganizationNotFound()
        self._send(
            mail_from,
            mail_to,
            org=org,
            email=mail_from,
            reminder=reminder)


class GroupLeadersEmail(LifeloopEmail):
    TEMPLATE = "to_group_leaders.html"
    SUBJECT = "LifeLoop.Live Group Leaders Email From Website"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a new group leaders email from '%s' to '%s'",
                  mail_from, mail_to)
        group = kwargs.get("group")
        if not group:
            raise exception.GroupNotFound()
        subject = kwargs.get("subject")
        message = kwargs.get("message")
        user = kwargs.get("user")
        self._send(
            mail_from,
            mail_to,
            group=group,
            user=user,
            subject=subject,
            message=message)


class GroupMassEmail(LifeloopEmail):
    TEMPLATE = "to_group.html"
    SUBJECT = "LifeLoop.Live Group Email From Website"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a new group mass email from '%s' to '%s'",
                  mail_from, mail_to)
        group = kwargs.get("group")
        if not group:
            raise exception.GroupNotFound()
        subject = kwargs.get("subject")
        message = kwargs.get("message")
        user = kwargs.get("user")
        self._send(
            mail_from,
            mail_to,
            group=group,
            user=user,
            subject=subject,
            message=message)


class OrgMassEmail(LifeloopEmail):
    TEMPLATE = "to_org.html"
    SUBJECT = "LifeLoop.Live Organization Email From Website"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a new group mass email from '%s' to '%s'",
                  mail_from, mail_to)
        org = kwargs.get("org")
        if not org:
            raise exception.GroupNotFound()
        subject = kwargs.get("subject")
        message = kwargs.get("message")
        user = kwargs.get("user")
        self._send(
            mail_from,
            mail_to,
            org=org,
            user=user,
            subject=subject,
            message=message)


class RequestAcknowledgedEmail(LifeloopEmail):
    TEMPLATE = "request_acknowledged.html"
    SUBJECT = "LifeLoop.Live Request Acknowledged"

    def send(self, mail_from, mail_to, **kwargs):
        notification = kwargs["notification"]
        self._send(mail_from, mail_to, notification=notification)


class ContactEmail(LifeloopEmail):
    TEMPLATE = "contact.html"
    SUBJECT = "LifeLoop.Live Contact Form"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a contact form email from '%s' to '%s'",
                  mail_from, mail_to)
        name = kwargs.get("name")
        phone = kwargs.get("phone")
        message = kwargs.get("message")
        self._send(
            mail_from,
            mail_to,
            name=name,
            email=mail_from,
            phone=phone,
            message=message)


class UserExistsRegistrationEmail(LifeloopEmail):
    TEMPLATE = "user_exists.html"
    SUBJECT = "LifeLoop.Live User Already Exists"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a user exists registration email from '%s' to '%s'",
                  mail_from, mail_to)
        url = "{}{}".format(DOMAIN, flask.url_for('forgot_password'))
        self._send(mail_from, mail_to, forgot_password_url=url)


class GroupOrganizationAddRequestEmail(LifeloopEmail):
    TEMPLATE = "group_org_add_request.html"
    SUBJECT = "LifeLoop.Live Request to Add Organization to Group"

    def send(self, mail_from, mail_to, **kwargs):
        LOG.debug("Sending a new group join request email from '%s' to '%s'",
                  mail_from, mail_to)
        group = kwargs.get("group")
        org = kwargs.get("org")
        reminder = kwargs.get("reminder")
        if not group:
            raise exception.GroupNotFound()
        if not org:
            raise exception.OrganizationNotFound()
        self._send(
            mail_from,
            mail_to,
            group=group,
            email=mail_from,
            org=org,
            reminder=reminder)


if not EMAIL_DRIVER:
    driver_name = CONF.get("email.driver")
    if driver_name.lower() == "mailgundriver":
        EMAIL_DRIVER = MailgunDriver()
    else:
        EMAIL_DRIVER = SendmailDriver()
