import datetime

from lifeloopweb.helpers.test_helper import Helper
import tests

helper = Helper()

class TestGetTimeZone(tests.TestBase):
    def test_only_numeric_phone_number(self):
        timezone = 'America/Chicago'
        dt = datetime.datetime(2017, 7, 4, 10, 12)
        result = helper.get_utc_date_time(timezone, dt)
        assert result == datetime.datetime(
            2017, 7, 4, 15, 12, tzinfo=datetime.timezone.utc)

    def test_datetime_offset(self):
        timezone = 'America/Chicago'
        dt = datetime.datetime(2017, 7, 4, 10, 12)
        result = helper.datetime_offset(dt, timezone)
        assert result == '07/04/2017 05:12 AM'

    def test_date_only_offset(self):
        timezone = 'America/Chicago'
        dt = datetime.datetime(2017, 7, 4, 10, 12)
        result = helper.date_only_offset(dt, timezone)
        assert result == '07/04/2017'

    def test_time_only_offset(self):
        timezone = 'America/Chicago'
        dt = datetime.datetime(2017, 7, 4, 10, 12)
        result = helper.time_only_offset(dt, timezone)
        assert result == '05:12 AM'

    def test_day_of_week(self):
        timezone = 'America/Chicago'
        dt = datetime.datetime(2017, 7, 4, 10, 12)
        result = helper.day_of_week(dt, timezone)
        assert result == 'Tuesday'
