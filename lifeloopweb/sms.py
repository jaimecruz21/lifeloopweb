import re
import requests
from requests.auth import HTTPBasicAuth

from lifeloopweb import config
from lifeloopweb import logging


SMS_DRIVER = None
CONF = config.CONF
LOG = logging.get_logger(__name__)


class SmsDriver(object):
    def send_text(self, destination_phone_number, message):
        raise NotImplementedError("Parent SmsDriver has no implementation")

    @staticmethod
    def only_numeric_phone_number(phone_number):
        only_numeric_phone = re.compile(r'[^\d]+')
        return only_numeric_phone.sub('', phone_number)


class OrcaWaveDriver(SmsDriver):
    REQUEST_URL = 'https://messageapi.orcawave.net/v4/messages'

    def __init__(self):
        LOG.debug("Initializing OrcaWaveDriver")
        self._key = CONF.get("orcawave.api.key")
        self._secret = CONF.get("orcawave.secret")
        self._source = CONF.get("orcawave.phone.number1")
        super().__init__()

    def send_text(self, destination_phone_number, message):
        LOG.debug("Sending text to '%s' with content '%s'",
                  destination_phone_number, message)
        phone_number = self.only_numeric_phone_number(destination_phone_number)
        request = requests.post(self.REQUEST_URL,
                                data={'source': self._source,
                                      'destination': phone_number,
                                      'messageText': message},
                                auth=HTTPBasicAuth(self._key, self._secret))
        LOG.debug("Orcawave Send Text response status: %s",
                  request.status_code)
        return request.status_code == 200


def sms_driver():
    return SMS_DRIVER


if not SMS_DRIVER:
    driver = CONF.get("sms.driver")
    if driver.lower() == "orcawavedriver":
        SMS_DRIVER = OrcaWaveDriver()
