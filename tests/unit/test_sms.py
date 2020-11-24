from lifeloopweb import sms

import tests


class TestSms(tests.TestBase):
    def test_only_numeric_phone_number(self):
        result = sms.SmsDriver().only_numeric_phone_number("(210) 999-9999")
        assert result == "2109999999"
