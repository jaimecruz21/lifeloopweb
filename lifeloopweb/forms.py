#!/usr/bin/env python

import datetime
import arrow

from flask import session
import pytz
import us
import wtforms
from wtforms.csrf.session import SessionCSRF
from wtforms.ext.sqlalchemy.fields import (
    QuerySelectField, QuerySelectMultipleField)
from wtforms import validators
from wtforms.fields import html5

from lifeloopweb import config, logging, constants
from lifeloopweb.db import models


CONF = config.CONF
LOG = logging.get_logger(__name__)

PASSWORD_SPECIAL_CHARACTERS = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
PASSWORD_MINIMUM_LENGTH = "8"
PASSWORD_REGEX = (r"((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*["
                  + PASSWORD_SPECIAL_CHARACTERS + "]).{"
                  + PASSWORD_MINIMUM_LENGTH + ",})")

MONTHS_CHOICES = [(1, "January"), (2, "February"), (3, "March"), (4, "April"),
                  (5, "May"), (6, "June"), (7, "Jule"), (8, "August"),
                  (9, "September"), (10, "October"), (11, "November"),
                  (12, "December")]


def states():
    state_choices = [('', 'Select state')]
    state_choices += list(us.states.mapping('abbr', 'abbr').items())
    return state_choices


def organizations():
    return [(str(o.id), o.name) for o in
            models.Session.query(
                models.Organization.id, models.Organization.name).filter(
                    models.Organization.activated_at.isnot(None)).order_by(
                        models.Organization.name).all()]


def age_ranges():
    return models.Session.query(models.AgeRange).order_by(
        models.AgeRange.priority).all()


def group_types():
    return models.Session.query(models.GroupType).all()


def link_types():
    return models.Session.query(models.LinkType).all()


def org_role_choices():
    return models.Session.query(models.OrganizationRole).all()


def meeting_time_types():
    return models.Session.query(models.MeetTimeType).order_by(
        models.MeetTimeType.priority).all()


def privacy_setting_choices():
    return [(str(p.id), p.description) for p in
            models.Session.query(
                models.GroupPrivacySetting.id,
                models.GroupPrivacySetting.description).order_by(
                    models.GroupPrivacySetting.priority).all()]


def gender_focus_choices():
    return [('', 'Men and Women'), ('M', 'Men'), ('F', 'Women')]


def zoom_meeting_duration_choices():
    return [('15', '15 min'),
            ('30', '30 min'),
            ('45', '45 min'),
            ('60', '1 hr'),
            ('75', '1 hr 15 min'),
            ('90', '1 hr 30 min'),
            ('105', '1 hr 45 min'),
            ('120', '2 hrs'),
            ('135', '2 hrs 15 min'),
            ('150', '2 hrs 30 min'),
            ('165', '2 hrs 45 min'),
            ('180', '3 hrs'),
            ('195', '3 hrs 15 min'),
            ('210', '3 hrs 30 min'),
            ('225', '3 hrs 45 min'),
            ('240', '4 hrs'),
            ('255', '4 hrs 15 min'),
            ('270', '4 hrs 30 min'),
            ('285', '4 hrs 45 min'),
            ('300', '5 hrs')]


def meeting_types():
    return [('', 'Choose Meeting Type...'),
            (str(models.ZoomMeeting.SCHEDULED_MEETING), 'Schedule Meeting'),
            (str(models.ZoomMeeting.REPEATED_MEETING), 'Weekly Meeting')]


class DynamicSelectField(wtforms.SelectField):
    """
    A SelectField that skips validations, allowing Javascript to
    populate it instead of it coming from the server side.

    Let someone else do the validatin'! It ain't my job."""

    def pre_validate(self, form):
        pass


class ToggleWidget(object):
    """
    Renders a list of fields as a `ul` or `ol` list.

    This is used for fields which encapsulate many inner fields as subfields.
    The widget will try to iterate the field to get access to the subfields and
    call them to render them.

    If `prefix_label` is set, the subfield's label is printed before the field,
    otherwise afterwards. The latter is useful for iterating radios or
    checkboxes.
    """
    def __init__(self, prefix_label=True):
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = ['']
        for subfield in field:
            html.append('<div class="row toggle">')
            if self.prefix_label:
                html.append('%s' % (subfield()))
            else:
                html.append('<li>%s %s</li>' % (subfield(), subfield.label))
            html.append('</div>')
        return wtforms.widgets.HTMLString(''.join(html))


class MultiQuerySelectField(QuerySelectMultipleField):
    widget = ToggleWidget()
    option_widget = wtforms.widgets.CheckboxInput()


class MyBaseForm(wtforms.Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        secret = CONF.get("csrf.secret.key")
        csrf_secret = str.encode(secret)
        csrf_time_limit = arrow.Arrow.utcnow().replace(minutes=20).utcoffset()

        @property
        def csrf_context(self):
            return session


class BirthdayMixin(MyBaseForm):
    month_of_birth = wtforms.SelectField(
        "Month", [wtforms.validators.DataRequired()], coerce=int,
        choices=MONTHS_CHOICES)
    day_of_birth = wtforms.SelectField(
        "Day", [wtforms.validators.DataRequired()], coerce=int)
    year_of_birth = wtforms.SelectField(
        "Year", [wtforms.validators.DataRequired()], coerce=int)

    def __init__(self, *args, **kwargs):
        super(BirthdayMixin, self).__init__(*args, **kwargs)
        year_max = datetime.datetime.now().year - int(
            CONF.get('user.minyears'))
        year_min = year_max - 100
        self.year_of_birth.choices = [
            (i, i) for i in range(year_min, year_max + 1)]
        self.day_of_birth.choices = [(i, i) for i in range(32) if i]
        if 'obj' in kwargs:
            birthday = kwargs['obj'].date_of_birth
            self.month_of_birth.data = birthday.month
            self.day_of_birth.data = birthday.day
            self.year_of_birth.data = birthday.year

    def validate_year_of_birth(self, field):
        min_years = int(CONF.get("user.minyears"))
        year = field.data
        month = self.month_of_birth.data
        day = self.day_of_birth.data
        date = datetime.date(year, month, day)
        birthday = arrow.Arrow.fromdate(date).to("utc")
        minimum_age = arrow.Arrow.utcnow()
        minimum_age = minimum_age.replace(years=-min_years)

        if birthday > minimum_age:
            raise validators.ValidationError(
                "You must be at least {} years old to sign up".format(
                    abs(min_years)))


class LoginForm(MyBaseForm):
    email = wtforms.StringField('Email', [wtforms.validators.Email()])
    password = wtforms.PasswordField(
        'Password', [wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Submit')


class ContactForm(MyBaseForm):
    name = wtforms.StringField("Name", [wtforms.validators.DataRequired()])
    email = html5.EmailField("Email", [wtforms.validators.Email(),
                                       wtforms.validators.DataRequired()])
    phone = wtforms.StringField("Phone")
    message = wtforms.TextAreaField("Message",
                                    [wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField("Submit")


class ForgotPasswordForm(MyBaseForm):
    email = wtforms.StringField('Email', [wtforms.validators.Email()])
    submit = wtforms.SubmitField('Reset Password')


class RegisterEmailForm(MyBaseForm):
    email = wtforms.StringField('Email', [wtforms.validators.Email()])
    submit = wtforms.SubmitField('Register')


class RegisterForm(BirthdayMixin):
    first_name = wtforms.StringField(
        "First Name", [wtforms.validators.DataRequired()])
    last_name = wtforms.StringField(
        "Last Name", [wtforms.validators.DataRequired()])
    email = wtforms.StringField("Email")
    city = wtforms.StringField("City", [wtforms.validators.DataRequired()])
    timezone = DynamicSelectField("Timezone", choices=[])
    phone_number = wtforms.StringField("Phone Number")
    opt_in_texts = wtforms.BooleanField(
        "I authorize LifeLoop.Live organization and group leaders to send text"
        " messages to my mobile number")
    opt_in_emails = wtforms.BooleanField(
        "I authorize LifeLoop.Live organization and group leaders to send"
        " emails to the email address I have provided")
    password = wtforms.PasswordField("Password", [
        wtforms.validators.DataRequired(),
        wtforms.validators.Regexp(
            PASSWORD_REGEX,
            message=(
                "Invalid password - password must be at least {} "
                "characters long and please use at least one capital "
                "letter, one lowercase letter, one number and one "
                "special character ({})".format(
                    PASSWORD_MINIMUM_LENGTH,
                    PASSWORD_SPECIAL_CHARACTERS))),
        wtforms.validators.EqualTo("confirm", message="Passwords must match")
    ])
    confirm = wtforms.PasswordField("Confirm Password",
                                    [wtforms.validators.DataRequired()])
    privacy_and_terms_agreement = wtforms.BooleanField(
        "Agree to Privacy and Terms",
        validators=[wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField("Register")

    def validate_timezone(self, field):
        try:
            pytz.timezone(field.data)
        except pytz.UnknownTimeZoneError:
            raise validators.ValidationError(
                "'{}' is not a valid timezone".format(field))


class MassEmailForm(MyBaseForm):
    recipient = wtforms.SelectField('Recipient', choices=[], coerce=str)
    subject = wtforms.StringField('Subject', [wtforms.validators.DataRequired()])
    message = wtforms.TextAreaField(
        'Message', [wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Send Email')


class ChartFilterForm(MyBaseForm):
    duration = wtforms.HiddenField('Duration')
    chart_id = wtforms.HiddenField('Chart ID')


class RoleForm(MyBaseForm):
    role = wtforms.SelectField('', choices=[], coerce=str)
    submit = wtforms.SubmitField('Update')


class GroupUserRoleForm(MyBaseForm):
    role = wtforms.SelectField('', choices=[])
    cohost_meeting = wtforms.BooleanField(
        'Can Cohost Meetings', validators=[wtforms.validators.Optional()])
    submit = wtforms.SubmitField('Update')


class GroupSearchForm(MyBaseForm):
    name = wtforms.StringField('Name')
    city = wtforms.StringField('City')
    state = wtforms.SelectField('State', choices=states())
    zip_code = wtforms.StringField('Zip')
    group_category = QuerySelectField('Group Category',
                                      query_factory=group_types,
                                      allow_blank=True)
    gender_focus = wtforms.RadioField(
        'Gender Focus',
        choices=gender_focus_choices(),
        default='')
    age_range = QuerySelectField(
        'Target Age Range',
        query_factory=age_ranges,
        allow_blank=True)
    submit = wtforms.SubmitField('Search')


class OrgSearchForm(MyBaseForm):
    name = wtforms.StringField('Organization Name')
    city = wtforms.StringField('City')
    state = wtforms.SelectField('State', choices=states())
    zip_code = wtforms.StringField('Zip')
    submit = wtforms.SubmitField('Search')


class PasswordResetForm(MyBaseForm):
    password = wtforms.PasswordField('New Password', [
        wtforms.validators.DataRequired(),
        wtforms.validators.Regexp(
            PASSWORD_REGEX,
            message=("Invalid password - password must be at least {} "
                     "characters long and please use at least one capital "
                     "letter, one lowercase letter, one number and one "
                     "special character ({})".format(
                         PASSWORD_MINIMUM_LENGTH,
                         PASSWORD_SPECIAL_CHARACTERS))),
        wtforms.validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = wtforms.PasswordField('Confirm Password')
    submit = wtforms.SubmitField('Reset')


class UserProfileForm(BirthdayMixin):
    first_name = wtforms.StringField(
        'First Name', [wtforms.validators.DataRequired()])
    last_name = wtforms.StringField(
        'Last Name', [wtforms.validators.DataRequired()])
    email = wtforms.StringField('Email', [wtforms.validators.Email()])
    timezone = DynamicSelectField("Timezone", choices=[])
    phone_number = wtforms.StringField('Phone Number')
    timezone_default = wtforms.HiddenField()
    opt_in_texts = wtforms.BooleanField(
        'I authorize LifeLoop.Live organization and group leaders to send text'
        ' messages to my mobile number')
    opt_in_emails = wtforms.BooleanField(
        'I authorize LifeLoop.Live organization and group leaders to send'
        ' emails to the email address I have provided')
    city = wtforms.StringField('City')
    submit = wtforms.SubmitField('Save Changes')


class GroupNewForm(MyBaseForm):
    name = wtforms.StringField('Name', [wtforms.validators.DataRequired()])
    user_is_leader = wtforms.BooleanField('I will be the group leader')
    owner = wtforms.StringField('Group Leader')
    privacy_settings = wtforms.RadioField('Group Privacy Setting', choices=[])
    anonymous = wtforms.BooleanField('Anonymous?')
    description = wtforms.TextAreaField('Description')
    member_limit = wtforms.IntegerField(
        'Maximum Number of Members',
        validators=[wtforms.validators.Optional()])
    group_category = QuerySelectField('Group Category',
                                      query_factory=group_types,
                                      allow_blank=True)
    gender_focus = wtforms.RadioField(
        'Gender Focus',
        choices=gender_focus_choices(),
        default='')
    age_range = QuerySelectField(
        'Target Age Range',
        query_factory=age_ranges,
        allow_blank=True)
    meet_times = MultiQuerySelectField(query_factory=meeting_time_types,
                                       allow_blank=True)
    org = wtforms.SelectField(
        'Which organization is this group a part of?', coerce=str,
        validators=[wtforms.validators.DataRequired()])
    group_image_file = wtforms.FileField(
        'Group Image  - Image must be at least 1000px wide and 1000px tall.'
        ' wide and 250px tall.')
    upload_and_crop = wtforms.SubmitField('UPLOAD')
    x_hidden = wtforms.HiddenField()
    y_hidden = wtforms.HiddenField()
    w_hidden = wtforms.HiddenField()
    h_hidden = wtforms.HiddenField()
    allocated_quantity = wtforms.IntegerField('Add Group Leaders',
                                              [wtforms.validators.Optional()],
                                              default=0)
    submit = wtforms.SubmitField('Save Group')


class GroupEditForm(MyBaseForm):
    name = wtforms.StringField('Name')
    description = wtforms.TextAreaField('Description')
    member_limit = wtforms.IntegerField(
        'Maximum Number of Members',
        validators=[wtforms.validators.Optional()])
    privacy_settings = wtforms.RadioField(
        'Privacy Settings',
        choices=[])
    anonymous = wtforms.BooleanField('Anonymous?')
    age_range = QuerySelectField(
        'Target Age Range',
        query_factory=age_ranges,
        allow_blank=True)
    gender_focus = wtforms.RadioField(
        'Gender Focus',
        choices=[('', 'Men and Women'), ('M', 'Men'), ('F', 'Women')],
        default='')
    group_category = QuerySelectField('Group Category',
                                      query_factory=group_types,
                                      allow_blank=True)
    meet_times = MultiQuerySelectField(query_factory=meeting_time_types,
                                       allow_blank=True)
    submit = wtforms.SubmitField('Update General Information')


class OrgForm(MyBaseForm):
    name = wtforms.StringField(
        'Name', validators=[wtforms.validators.DataRequired()])
    custom_url = wtforms.StringField(
        'Custom URL (no spaces or special characters)')
    description = wtforms.TextAreaField('Description')
    service_times = wtforms.StringField('Service Times')
    date_founded = wtforms.DateField(
        'Date Founded', format=constants.DATE_FORMAT,
        validators=[wtforms.validators.Optional()])
    show_address = wtforms.BooleanField(
        'Show Address?', validators=[wtforms.validators.Optional()])
    street_address = wtforms.StringField(
        'Street Address', validators=[wtforms.validators.DataRequired()])
    city = wtforms.StringField(
        'City', validators=[wtforms.validators.DataRequired()])
    state = wtforms.SelectField(
        'State', choices=states(),
        validators=[wtforms.validators.DataRequired()])
    zip_code = wtforms.StringField(
        'Zip Code', validators=[wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Submit')


class OrgFormWithOwner(OrgForm):
    owner = wtforms.StringField(
        'Owner', validators=[wtforms.validators.DataRequired()])


class LinkForm(MyBaseForm):
    link_type = QuerySelectField('Type',
                                 query_factory=link_types,
                                 get_label='description',
                                 allow_blank=True)
    link = wtforms.StringField('URL')
    submit = wtforms.SubmitField('Save')


class ConfirmForm(MyBaseForm):
    confirm = wtforms.SubmitField('Confirm')
    confirm_checkbox = wtforms.BooleanField(
        '', validators=[wtforms.validators.Optional()])


class AddMemberForm(MyBaseForm):
    return_url = wtforms.HiddenField()
    email = wtforms.StringField('Email', [wtforms.validators.Email(),
                                          wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Add Member')


class GroupAddOrgForm(MyBaseForm):
    orgs = wtforms.SelectField('Organization', choices=[], validators=[
        wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Add Organization')


class GroupLeadersEmailForm(MyBaseForm):
    subject = wtforms.StringField('Subject',
                                  [wtforms.validators.DataRequired()])
    message = wtforms.TextAreaField(
        'Message', [wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Send Email')


class TextMessageForm(MyBaseForm):
    recipient = wtforms.SelectField('Recipient', choices=[], coerce=str)
    message = wtforms.TextAreaField(
        'Message', [wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Send Text')


class GroupAddDocumentForm(MyBaseForm):
    filename = wtforms.StringField('Friendly File Name',
                                   [wtforms.validators.DataRequired()])
    file = wtforms.FileField('Upload a file')
    submit = wtforms.SubmitField('Add')


class GroupAddGoogleDocForm(MyBaseForm):
    filename = wtforms.StringField('Friendly Link Name')
    link = wtforms.StringField('Import Share Link from Google Drive')
    submit = wtforms.SubmitField('Add')


class GroupMeetingForm(MyBaseForm):
    meeting_id = wtforms.HiddenField()
    start_datetime = wtforms.DateTimeField(
        '', format=constants.DATE_TIME_FORMAT)
    topic = wtforms.TextAreaField(
        'Meeting Topic', [wtforms.validators.DataRequired()])
    duration = wtforms.SelectField(
        'Duration', choices=zoom_meeting_duration_choices(),
        validators=[wtforms.validators.DataRequired()])
    meeting_type = wtforms.SelectField('Type', choices=meeting_types())
    repeat_end_date = wtforms.DateField(
        'Repeat End Date (blank means no end date)',
        format=constants.DATE_FORMAT,
        validators=[wtforms.validators.Optional()])
    submit = wtforms.SubmitField('Add')


class LicenseUpdateForm(MyBaseForm):
    quantity = wtforms.IntegerField('Additional group leaders')
    submit = wtforms.SubmitField('Update')


class CardInfoForm(MyBaseForm):
    full_number = wtforms.StringField(
        'Card Number', [wtforms.validators.DataRequired()])
    expiration_month = wtforms.IntegerField(
        'Card expiration month',
        [wtforms.validators.DataRequired(), wtforms.validators.NumberRange(
            min=1, max=12)])
    expiration_year = wtforms.IntegerField(
        'Card expiration year', [wtforms.validators.DataRequired()])
    billing_address = wtforms.StringField(
        'Billing Address', [wtforms.validators.DataRequired()])
    billing_city = wtforms.StringField(
        'Billing City', [wtforms.validators.DataRequired()])
    billing_state = wtforms.StringField(
        'Billing State', [wtforms.validators.DataRequired()])
    billing_country = wtforms.StringField(
        'Billing Country', [wtforms.validators.DataRequired()])
    billing_zip = wtforms.IntegerField(
        'Billing ZIP', [wtforms.validators.DataRequired()])
    coupon_code = wtforms.StringField('Coupon Code')
    privacy_and_terms_agreement = wtforms.BooleanField(
        "Agree to Privacy and Terms", [wtforms.validators.DataRequired()])
    submit = wtforms.SubmitField('Send')

class PageContentForm(MyBaseForm):
    title = wtforms.TextAreaField("Page Title")
    content = wtforms.TextAreaField("Page Content")
    submit = wtforms.SubmitField('Submit')
