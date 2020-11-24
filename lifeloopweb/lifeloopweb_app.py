#!/usr/bin/env python
# pylint: disable=singleton-comparison, unexpected-keyword-arg, no-value-for-parameter, too-many-nested-blocks

import datetime
import re
import traceback
from urllib.parse import urlparse, urljoin
import werkzeug

import flask
from flask import url_for, redirect, render_template
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, login_required, login_user, logout_user, current_user)
from flask_recaptcha import ReCaptcha
from sqlalchemy import orm

from lifeloopweb import __version__
from lifeloopweb.app import (groups, images, links, notifications,
                             organizations, users, utils as app_utils)
from lifeloopweb import (config, email, exception,
                         forms, logging, signature)
from lifeloopweb.db import models
from lifeloopweb.webpack import webpack
from lifeloopweb.helpers.base_helper import Helper

login_manager = LoginManager()
CONF = config.CONF
LOG = logging.get_logger(__name__)
ENV = CONF.get('environment', 'development').lower()
GOOGLE = CONF.get('google.analytics.id')

helper = Helper()


def create_app():
    template_path = CONF.get('flask.templates.folder')
    static_path = CONF.get('flask.static.folder')
    flask_app = flask.Flask(__name__,
                            template_folder=template_path,
                            static_folder=static_path)
    flask_app.secret_key = str.encode(CONF.get('csrf.secret.key'))
    flask_app.config['WEBPACK_MANIFEST_PATH'] = CONF.get(
        'webpack.manifest.path')

    register_extensions(flask_app)

    # Register blueprints
    blueprint_mods = [groups, images, links, notifications, organizations, users]
    for mod in blueprint_mods:
        flask_app.register_blueprint(mod.BLUEPRINT, url_prefix=mod.URL_PREFIX)
    return flask_app


def register_extensions(flask_app):
    webpack.init_app(flask_app)
    login_manager.init_app(flask_app)
    login_manager.login_view = 'login'


app = create_app()
app.config.update(
    RECAPTCHA_ENABLED=CONF.get("recaptcha.enabled"),
    RECAPTCHA_SITE_KEY=CONF.get("recaptcha.site.key"),
    RECAPTCHA_SECRET_KEY=CONF.get("recaptcha.secret.key"),
    RECAPTCHA_THEME=CONF.get("recaptcha.theme"),
    RECAPTCHA_TYPE=CONF.get("recaptcha.type"),
    RECAPTCHA_SIZE=CONF.get("recaptcha.size"),
    RECAPTCHA_TABINDEX=CONF.get("recaptcha.tabindex"),
)
bcrypt = Bcrypt(app)
recaptcha = ReCaptcha(app=app)

if ENV not in ['development', 'test']:
    from raven.contrib.flask import Sentry
    app.config.update(
        SENTRY_USER_ATTRS=CONF.get_array("sentry.user.attrs"),
        SENTRY_CONFIG={'release': __version__,
                       'tags': {'environment': ENV},
                       'url': CONF.get('site.domain')}
    )
    sentry = Sentry(app, logging=True, level=logging.ERROR)


@app.template_filter('offset')
def datetime_with_timezone_offset(value):
    return helper.datetime_offset(value, current_user.timezone)


@app.template_filter('image_scale')
def image_scale(cloudinary_image_url):
    splits = cloudinary_image_url.split('upload')
    return "{}upload/h_250,h_250,c_scale,c_pad,b_black{}".format(
        splits[0], splits[1])


@app.template_filter('image_pct')
def image_pct(cloudinary_image_url):
    splits = cloudinary_image_url.split('upload')
    return "{}upload/w_250,h_250,c_scale{}".format(
        splits[0], splits[1])


def is_safe_url(target):
    ref_url = urlparse(flask.request.host_url)
    test_url = urlparse(urljoin(flask.request.host_url, target))
    return (test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc)


@login_manager.user_loader
def load_user(userid):
    with models.transaction() as session:
        user_query = session.query(models.User)
        return user_query.filter(models.User.id == userid).first()


@login_manager.unauthorized_handler
def handle_needs_login():
    flask.flash("You have to be logged in to access this page.")
    return redirect(url_for('login', next=flask.request.path))


app_utils.wrap_context(app)


@app.context_processor
def inject_common_variables():
    user_notifications = []
    if current_user.is_authenticated:
        user_notifications = current_user.new_notifications
    context = {
        'success_flash_timeout': CONF.get(
            'success.flash.timeout.in.seconds', 10),
        'current_year': datetime.date.today().year,
        'environment': ENV,
        'analytics_id': GOOGLE,
        'notifications': user_notifications,
        'search_form': forms.OrgSearchForm()
    }
    return context


@app.teardown_appcontext
def teardown_request(_exception=None):
    models.teardown()


@app.route("/<vanity_name>")
def org_by_vanity_name(_ctxt, vanity_name):
    try:
        possible_vanity_name = vanity_name.lower()
        vanity_regex = re.compile("^[a-z0-9_]+$")
        if not vanity_regex.match(possible_vanity_name):
            raise Exception("request contains illegal characters")
        o = models.Organization.get_by_vanity_name(possible_vanity_name)
        if o:
            return organizations.helper.show(o)
    except Exception:
        # Not a LOG.exception because I don't want an email every time someone
        # tries to grief us
        LOG.info("Error processing possible vanity name. %s",
                 flask.request.path)
        LOG.info(traceback.format_exc())
    return render_template('error.html'), 404


# TODO: make this handle all exceptions
@app.errorhandler(werkzeug.exceptions.BadRequest)
@app.errorhandler(werkzeug.exceptions.Unauthorized)
@app.errorhandler(werkzeug.exceptions.Forbidden)
@app.errorhandler(werkzeug.exceptions.MethodNotAllowed)
@app.errorhandler(werkzeug.exceptions.InternalServerError)
@app.errorhandler(werkzeug.exceptions.RequestEntityTooLarge)
def handle_error(error):
    LOG.exception('Showing Friendly Error Page: %s', error)
    return render_template('error.html')


@app.errorhandler(404)
def page_not_found(e):
    LOG.info('Not Found %s', e)
    return render_template('404.html'), 404


@app.route('/', methods=['GET', 'POST'])
def index(_ctxt):
    groups_limit = CONF.get('max.groups.on.homepage')
    cls = models.Group
    query_filter = [
        models.GroupPrivacySetting.description.like('Public%'),
        cls.archived_at.is_(None)]
    order_by = cls.id.desc()

    if flask.request.method == 'POST':
        form = flask.request.get_json()
        if form.get('age'):
            query_filter.append(cls.age_range_id == form['age'])
        if form.get('gender') or form.get('gender') == '':
            query_filter.append(cls.gender_focus == form['gender'])
        if form.get('group_types'):
            query_filter.append(cls.group_type_id.in_(form['group_types']))
        if form.get('order'):
            order_by = cls.clicks.desc()

    query = models.Session.query(cls).join(
        cls.privacy_settings
    ).filter(*query_filter).order_by(
        order_by
    ).limit(groups_limit)

    if flask.request.method == 'POST':
        return render_template(
            '_partials/featured_groups.html', group_list=query.all())

    filter_ages = models.Session.query(models.AgeRange).options(
        orm.load_only('id', 'description')).all()
    filter_group_types = models.Session.query(models.GroupType).options(
        orm.load_only('id', 'description')).all()

    wtforms = {
        'confirm': forms.ConfirmForm(),
        'contact': forms.ContactForm()
    }

    # TODO: see models.py Group.gender_focus note
    context = {
        'group_list': query.all(),
        'filter': {
            'genders': [
                ('', "Men and Women"),
                ('M', "Men's Group"),
                ('F', "Women's Group")
            ],
            'ages': filter_ages,
            'group_types': filter_group_types
        },
        'wtforms': wtforms
    }
    return render_template('index.html', **context)


@app.route('/version')
def version(_ctxt):
    try:
        return render_template('version.html')
    except Exception:
        return str("N/A")


@app.route('/logout')
@login_required
def logout(_ctxt):
    logout_user()
    flask.flash('Successfully logged out.', 'success')
    return redirect(url_for("index"))


@app.route('/profile', methods=['GET'])
@login_required
def profile(_ctxt):
    return redirect(url_for("users.show", user_id=current_user.id))


@app.route('/login', methods=['GET', 'POST'])
def login(_ctxt):
    if current_user.is_authenticated:
        return redirect('profile')
    form = forms.LoginForm(flask.request.form)
    if flask.request.method == 'POST':
        if form.validate():
            user = models.User.get_by_email(form.email.data)
            if not user:
                flask.flash('Invalid login credentials.', 'danger')
            elif user.verified_at is None:
                flask.flash("Your account has not been activated. Please "
                            "check your email to verify your account",
                            "danger")
            else:
                try:
                    valid_password = bcrypt.check_password_hash(
                        user.hashed_password, form.password.data)
                    if not valid_password:
                        flask.flash('Invalid login credentials.', 'danger')
                    else:
                        login_user(user)
                        flask.flash('Logged in successfully.', 'success')
                        return redirect_dest(url_for('users.show',
                                                     user_id=user.id))
                except ValueError:
                    LOG.exception(
                        "User %s hasn't updated their password from"
                        " legacy system", form.email.data)
                    flask.flash('Invalid login credentials.', 'danger')
                    return redirect_dest(home=url_for('login'))
        else:
            app_utils.flash_errors(form)
    return render_template('login.html', form=form)


def redirect_dest(home):
    dest_url = flask.request.args.get('next', home)
    return redirect(dest_url)


@app.route('/register', methods=['POST'])
def register(_ctxt):
    form = forms.RegisterEmailForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    elif not recaptcha.verify():
        flask.flash("Invalid Captcha. Please make sure to confirm you "
                    "are human.", "danger")
    else:
        try:
            mail_from = CONF.get("email.mailfrom")
            mail_to = form.email.data

            # Don't leak emails to people just guessing, let them
            # think we're always sending something
            if not users.is_existing_user(form.email.data):
                r = email.RegistrationEmail()
                r.send(mail_from, mail_to,
                       return_route="register/validate")
            else:
                r = email.UserExistsRegistrationEmail()
                r.send(mail_from, mail_to,
                       return_route="forgot-password/validate")

            flask.flash("Validation email has been sent. "
                        "Please check your email box to "
                        "complete the registration.",
                        'success')
        except Exception:
            LOG.exception("Error sending registration token")
            flask.flash('There was an error getting you registered.'
                        ' Please try again later.', 'danger')
    return redirect(url_for('login'))


@app.route('/register/validate/<token>', methods=['GET', 'POST'])
def register_validation(_ctxt, token):
    form = forms.RegisterForm(flask.request.form)
    try:
        reg_email = email.RegistrationEmail()
        content = reg_email.decrypt_token(token)
        address = content.get('mail_to', None)
        if not address:
            raise signature.InvalidSignature()
        if address and users.is_existing_user(address):
            raise exception.UserAlreadyExists(email=address)
        form.email.default = address
    except (signature.InvalidSignature, exception.MalformedToken):
        flask.flash("Error occurred. Please restart registration process",
                    "danger")
        return redirect(url_for("login"))
    except exception.UserAlreadyExists:
        flask.flash("A user is already registered for {}."
                    " Please login instead.".format(address), "danger")
        return redirect(url_for("login"))

    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        else:
            try:
                app_utils.create_user_from_form(form)
                flask.flash("You've successfully registered."
                            " Please login to continue.",
                            'success')
                return redirect(url_for('login'))
            except Exception:
                LOG.exception("Error creating user via token registration")
                models.Session.rollback()
                flask.flash("There was an error getting you registered."
                            " Please try again later.",
                            'danger')
                return redirect(url_for('register'))
    form.email.data = address
    form_url = url_for("register_validation", token=token)
    context = {
        'form': form,
        'form_url': form_url,
        'minyears': CONF.get("user.minyears")
    }
    return render_template('register_after_email.html', **context)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password(_ctxt):
    form = forms.ForgotPasswordForm(flask.request.form)
    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        else:
            try:
                user = users.existing_user(form.email.data)
                if not user:
                    flask.flash("User with that email does not exist."
                                "  Please try a different email address.",
                                'danger')
                    return redirect(url_for('forgot_password'))
                mail_from = CONF.get("email.mailfrom")
                mail_to = form.email.data
                r = email.ForgotPasswordEmail()
                r.send(mail_from, mail_to,
                       return_route="forgot-password/validate")

                flask.flash("You've successfully sent a password reset email. "
                            "Please click the link in your email to "
                            "reset your password.",
                            'success')
                return redirect(url_for('login'))
            except Exception:
                LOG.exception("Forgot Password failed for user with email "
                              "'%s'", form.email.data)
                flask.flash('There was an error sending the password reset'
                            '  email.  Please try again later.',
                            'danger')
                return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html', form=form)


@app.route("/forgot-password/validate/<token>", methods=["GET"])
def forgot_password_validate(_ctxt, token):
    error_msg = "Error. Please start forgot password process over."
    try:
        forgot_email = email.ForgotPasswordEmail()
        content = forgot_email.decrypt_token(token)
        address = content.get('mail_to')
    except signature.InvalidSignature:
        flask.flash(error_msg, "danger")
        return redirect(url_for("forgot_password"))

    form = forms.PasswordResetForm(flask.request.form)
    user = models.User.get_by_email(address)
    if not user:
        flask.flash(error_msg, "danger")
        return redirect(url_for("forgot_password"))

    flask.flash("Please reset your password.", "success")
    context = {
        'form': form,
        'user_id': user.id,
        'token': token}
    return render_template("reset_password.html", **context)


@app.route('/reset-password', methods=['POST'])
@login_required
def password_reset(_ctxt):
    form = forms.PasswordResetForm(flask.request.form)
    if not form.validate():
        app_utils.flash_errors(form)
    else:
        password = form.password.data
        user = models.User.get(current_user.id)
        try:
            with models.transaction() as session:
                hashed_password = bcrypt.generate_password_hash(
                    password).decode('utf-8')
                user.hashed_password = hashed_password
                session.add(user)
            flask.flash("Password reset successfully!", 'success')
        except Exception:
            LOG.exception("Password reset failed for user id '%s'",
                          current_user.id)
            flask.flash("Error changing password.", 'danger')
    return redirect(url_for('users.show', user_id=current_user.id))


@app.route('/invite')
def invite(_ctxt):
    return render_template('invite.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact(_ctxt):
    form = forms.ContactForm(flask.request.form)
    if flask.request.method == 'POST':
        if not form.validate():
            app_utils.flash_errors(form)
        elif not recaptcha.verify():
            flask.flash("Invalid Captcha. Please make sure to confirm you "
                        "are human.", "danger")
        else:
            try:
                e = email.ContactEmail()
                e.send(
                    form.email.data,
                    CONF.get("support.email.address"),
                    **form.data)
                flask.flash('You successfully submitted your contact request,'
                            ' someone will contact you shortly.'
                            '  Thanks for your feedback/interest!',
                            'success')
                return redirect(url_for('contact'))
            except Exception:
                LOG.exception("Error sending contact form information")
                flask.flash('There was a problem submitting your contact '
                            'request. Sorry for the inconvenience. We will '
                            'fix this as soon as we can. Please try again '
                            'shortly.', 'danger')
    return render_template('contact-us.html', form=form)


# STATIC VIEWS
@app.route('/welcome', methods=['GET'])
def welcome(_ctxt):
    form = forms.LoginForm()
    context = dict(form=form)
    return render_template('welcome.html', **context)


@app.route('/how-it-works', methods=['GET'])
def how_it_works(_ctxt):
    return render_template('how-it-works.html')


@app.route('/privacy')
def privacy(_ctxt):
    page = helper.get_page_content('privacy')
    super_admin = False
    if current_user.is_authenticated and current_user.super_admin:
        super_admin = current_user.super_admin
    context = {
        'super_admin': super_admin,
        'title': 'Privacy Policy',
        'page_title': page.title,
        'page_content': page.content,
        'revision_date': page.created_at,
        'edit_url': url_for('privacy_edit')
    }
    return render_template(
        'privacy_and_terms.html', **context)

@app.route('/terms')
def terms(_ctxt):
    page = helper.get_page_content('terms')
    super_admin = False
    if current_user.is_authenticated and current_user.super_admin:
        super_admin = current_user.super_admin
    context = {
        'super_admin': super_admin,
        'title': 'Terms & Conditions',
        'page_title': page.title,
        'page_content': page.content,
        'revision_date': page.created_at,
        'edit_url': url_for('terms_edit')
    }
    return render_template(
        'privacy_and_terms.html', **context)


def page_editor(pagetype):
    if current_user.is_authenticated and current_user.super_admin:
        form = forms.PageContentForm(flask.request.form)
        if flask.request.method == 'POST':
            helper.edit_page_content(form, current_user.email, pagetype)
            return redirect(url_for(pagetype))
        last = helper.get_page_content(pagetype)
        context = {
            'title': "Edit " + pagetype,
            'form': form,
            'last': last,
            'edit_url': url_for(pagetype + '_edit')
        }
        return render_template('edit-content.html', **context)
    else:
        return redirect(url_for(pagetype))


@app.route('/privacy-edit', methods=['GET', 'POST'])
def privacy_edit(_ctxt):
    return page_editor('privacy')


@app.route('/terms-edit', methods=['GET', 'POST'])
def terms_edit(_ctxt):
    return page_editor('terms')

@app.route('/faq')
def faq(_ctxt):
    context = dict(contact_form=forms.ContactForm())
    return render_template('faq.html', **context)


def run_server():
    app.run()


if __name__ == "__main__":
    run_server()
