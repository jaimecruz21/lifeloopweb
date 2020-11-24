import pytest
import tests

from lifeloopweb import token, exception


class TestToken(tests.TestBase):
    def test_get_content(self):
        payload = {'a': 1, 'b': 2, 'c': 3}
        sig = token.create(payload)
        sig_decrypted = token.decrypt(sig)
        assert sig_decrypted == payload

    def test_get_exception_when_content_malformed(self):
        payload = {'a': 1, 'b': 2, 'c': 3}
        sig = token.create(payload)
        with pytest.raises(exception.MalformedToken):
            token.decrypt("{}{}".format(sig, "malform"))
