import pytest

from lifeloopweb.db.models import User
from lifeloopweb import exception
import tests


class TestUser(tests.TestBase):
    def test_get_email_from_full_name_and_email(self):
        full_name_and_email = "Jason Meridth (jason@meridth.io)"
        result = User.get_email_from_full_name_and_email(
            full_name_and_email)
        assert result == 'jason@meridth.io'

    def test_get_email_from_full_name_and_email_with_invalid_email(self):
        full_name_and_email = "invalid"
        with pytest.raises(exception.InvalidEmail):
            User.get_email_from_full_name_and_email(full_name_and_email)
