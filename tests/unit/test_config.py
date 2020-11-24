from lifeloopweb import config

import tests

CONF = config.CONF


# KEEP ALPHABETICAL PLEASE
class TestGetConfig(tests.TestBase):
    def test_get_allowed_file_extensions(self):
        value = CONF.get("allowed.video.extensions")
        assert value == "mpg,mp2,mpeg,mpe,mpv,webm,ogg,mp4,m4p,m4v,mov"

    def test_get_allowed_video_extensions(self):
        value = CONF.get("allowed.file.extensions")
        assert value == "txt,pdf,doc,docx,xls,xlsx,ppt,pptx"

    def test_get_aws_access_key_id(self):
        value = CONF.get("aws.access.key.id")
        assert value == "aws_access_key"

    def test_get_aws_secret_access_key(self):
        value = CONF.get("aws.secret.access.key")
        assert value == "aws_secret_access_key"

    def test_get_aws_bucket_name(self):
        value = CONF.get("aws.bucket.name")
        assert value == "aws_bucket_name"

    def test_get_allowed_image_extensions(self):
        value = CONF.get_array("allowed.image.extensions")
        assert value == ["jpg", "png", "jpeg", "gif"]

    def test_get_chargify_api_key(self):
        value = CONF.get("chargify.api.key")
        assert value == "chargify_api_key"

    def test_get_chargify_default_component_id(self):
        value = CONF.get("chargify.default.component.id", False)
        assert value

    def test_get_chargify_request_url(self):
        value = CONF.get("chargify.request.url")
        assert value == "chargify_request_url"

    def test_get_cloudinary_api_key(self):
        value = CONF.get("cloudinary.api.key")
        assert value == "cloudinary_api_key"

    def test_get_cloudinary_secret(self):
        value = CONF.get("cloudinary.secret")
        assert value == "cloudinary_secret"

    def test_get_cloudinary_upload_preset(self):
        value = CONF.get("cloudinary.upload.preset")
        assert value == "cloudinary_upload_preset"

    def test_get_csrf_secret_key(self):
        value = CONF.get("csrf.secret.key")
        assert value == "Ar3Iz#CEh@#zlYsr7q3KnsLc72oaCx!w"

    def test_get_database_connection_poolsize(self):
        value = CONF.get("database.connection.poolsize")
        assert value == "20"

    def test_get_database_connection_overflowpool(self):
        value = CONF.get("database.connection.overflowpool")
        assert value == "20"

    def test_get_database_connection_poolrecycle(self):
        value = CONF.get("database.connection.poolrecycle")
        assert value == "3600"

    def test_get_database_connection_debug(self):
        value = CONF.get("database.connection.debug")
        assert value == "False"

    def test_get_db_engine_url(self):
        value = CONF.get("db.engine.url")
        assert (
            value ==
            "mysql+pymysql://root:@database/lifeloopweb_test?charset=utf8")

    def test_get_disqus_public_key(self):
        value = CONF.get("disqus.public.key")
        assert value == "disqus_public_key"

    def test_get_disqus_secret_key(self):
        value = CONF.get("disqus.secret.key")
        assert value == "disqus_secret_key"

    def test_get_disqus_site_name(self):
        value = CONF.get("disqus.site.name")
        assert value == "disqus_site_name"

    def test_get_email_driver(self):
        value = CONF.get("email.driver")
        assert value == "SendmailDriver"

    def test_get_email_host(self):
        value = CONF.get("email.host")
        assert value == "mailhog"

    def test_get_email_mailfrom(self):
        value = CONF.get("email.mailfrom")
        assert value == "noreply@lifeloop.live"

    def test_get_email_port(self):
        value = CONF.get("email.port")
        assert value == "1025"

    def test_get_environment(self):
        value = CONF.get("environment")
        assert value == "test"

    def test_get_flask_static_folder(self):
        value = CONF.get("flask.static.folder")
        assert value == "build"

    def test_get_google_analytics_id(self):
        value = CONF.get("google.analytics.id")
        assert value == "google_analytics_id"

    def test_get_google_analytics_key_file_location(self):
        value = CONF.get("google.analytics.key.file.location")
        assert value == "google_analytics_key_file_location"

    def test_get_google_analytics_private_key_id(self):
        value = CONF.get("google.analytics.private.key.id")
        assert value == "google_analytics_private_key_id"

    def test_get_google_analytics_private_key(self):
        value = CONF.get("google.analytics.private.key")
        assert value == "google_analytics_private_key"

    def test_get_google_analytics_view_id(self):
        value = CONF.get("google.analytics.view.id")
        assert value == "google_analytics_view_id"

    def test_get_google_api_key(self):
        value = CONF.get("google.api.key")
        assert value == "google_api_key"

    def test_get_google_api_client_id(self):
        value = CONF.get("google.api.client.id")
        assert value == "google_api_client_id"

    def test_get_log_file_path(self):
        value = CONF.get("log.file.path")
        assert value == "lifeloop-{}.log"

    def test_get_logging_admins(self):
        value = CONF.get("logging.admins")
        assert value == "jason@meridth.io"

    def test_get_logging_error_email_from(self):
        value = CONF.get("logging.error_email_from")
        assert value == "server-error@lifeloop.live"

    def test_get_logging_error_email_level(self):
        value = CONF.get("logging.error_email_level")
        assert value == "ERROR"

    def test_get_loglevel(self):
        value = CONF.get("loglevel")
        assert value == "DEBUG"

    def test_get_mailgun_api_key(self):
        value = CONF.get("mailgun.api.key")
        assert value == "mailgun_api_key"

    def test_get_mailgun_domain(self):
        value = CONF.get("mailgun.domain")
        assert value == "mailgun_domain"

    def test_get_max_groups_on_homepage(self):
        value = CONF.get("max.groups.on.homepage")
        assert value == "40"

    def test_get_meeting_driver(self):
        value = CONF.get("meeting.driver")
        assert value == "ZoomMeetingDriver"

    def test_get_orcawave_api_key(self):
        value = CONF.get("orcawave.api.key")
        assert value == "orcawave_api_key"

    def test_get_orcawave_secret(self):
        value = CONF.get("orcawave.secret")
        assert value == "orcawave_secret"

    def test_get_orcawave_phone_number1(self):
        value = CONF.get("orcawave.phone.number1")
        assert value == "orcawave_phone_number1"

    def test_get_orcawave_phone_number2(self):
        value = CONF.get("orcawave.phone.number2")
        assert value == "orcawave_phone_number2"

    def test_get_orcawave_phone_number3(self):
        value = CONF.get("orcawave.phone.number3")
        assert value == "orcawave_phone_number3"

    def test_get_recaptcha_enabled(self):
        value = CONF.get("recaptcha.enabled")
        assert value == "True"

    def test_get_recaptcha_site_key(self):
        value = CONF.get("recaptcha.site.key")
        assert value == "recaptcha_site_key"

    def test_get_recaptcha_secret_key(self):
        value = CONF.get("recaptcha.secret.key")
        assert value == "recaptcha_secret_key"

    def test_get_recaptcha_type(self):
        value = CONF.get("recaptcha.type")
        assert value == "recaptcha_type"

    def test_get_recaptcha_size(self):
        value = CONF.get("recaptcha.size")
        assert value == "recaptcha_size"

    def test_get_recaptcha_tabindex(self):
        value = CONF.get("recaptcha.tabindex")
        assert value == "0"

    def test_get_sentry_dsn(self):
        value = CONF.get("sentry.dsn")
        assert value == "sentry_dsn"

    def test_get_sentry_user_attrs(self):
        value = CONF.get_array("sentry.user.attrs")
        assert value == ["first_name", "last_name", "email"]

    def test_get_signing_secret_key(self):
        value = CONF.get("signing.secret.key")
        assert value == "secret-test-key"

    def test_get_site_domain(self):
        value = CONF.get("site.domain")
        assert value == "http://127.0.0.1:5000"

    def test_get_sms_driver(self):
        value = CONF.get("sms.driver")
        assert value == "OrcaWaveDriver"

    def test_get_subscription_driver(self):
        value = CONF.get("subscription.driver")
        assert value == "subscription_driver"

    def test_get_subscription_old_users_week_starts(self):
        value = CONF.get("subscription.old.users.week.starts")
        assert value == "1"

    def test_get_success_flash_timeout_in_seconds(self):
        value = CONF.get("success.flash.timeout.in.seconds")
        assert value == "10"

    def test_get_support_email_address(self):
        value = CONF.get("support.email.address")
        assert value == "support@lifeloop.live"

    def test_get_token_expires_in_days(self):
        value = CONF.get("token.expires.in.days")
        assert value == "3"

    def test_get_token_expires_in_hours(self):
        value = CONF.get("token.expires.in.hours")
        assert value == "3"

    def test_get_user_minyears(self):
        value = CONF.get("user.minyears")
        assert value == "16"

    def test_get_webpack_manifest_path(self):
        value = CONF.get("webpack.manifest.path")
        assert value == "build/manifest.json"

    def test_get_zoom_api_key(self):
        value = CONF.get("zoom.api.key")
        assert value == "zoom_api_key"

    def test_get_zoom_api_secret(self):
        value = CONF.get("zoom.api.secret")
        assert value == "zoom_api_secret"

    def test_get_zoom_api_token(self):
        value = CONF.get("zoom.api.token")
        assert value == "zoom_api_token"

    def test_get_zoom_host_user_id(self):
        value = CONF.get("zoom.host.user.id")
        assert value == "zoom_host_user_id"
