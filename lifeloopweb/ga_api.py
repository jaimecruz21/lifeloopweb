import json
from pathlib import Path
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient import errors, discovery
from lifeloopweb import config, logging

CONF = config.CONF
LOG = logging.get_logger(__name__)

TYPE = 'service_account'
AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
AUTH_PROVIDER_X509_CERT_URL = 'https://www.googleapis.com/oauth2/v1/certs'


class GA(object):
    requests = []
    reports = []

    COUNTRY = {
        'dimensions': [{'name': 'ga:country'}],
        'metrics': [{'expression': 'ga:sessions'}],
        'orderBys': [{
            'fieldName': 'ga:sessions',
            'sortOrder': 'DESCENDING'
        }]
    }
    VISITS = {
        'dimensions': [
            {'name': 'ga:hour'},
            {'name': 'ga:date'}
        ],
        'metrics': [{'expression': 'ga:visits'}]
    }
    MALE = {
        'dimensions': [{'name': 'ga:userAgeBracket'}],
        'metrics': [{'expression': 'ga:sessions'}],
        'filters': [{
            'operator': 'EXACT',
            'dimensionName': 'ga:userGender',
            'expressions': ['male']
        }]
    }
    FEMALE = {
        'dimensions': [{'name': 'ga:userAgeBracket'}],
        'metrics': [{'expression': 'ga:sessions'}],
        'filters': [{
            'operator': 'EXACT',
            'dimensionName': 'ga:userGender',
            'expressions': ['female']
        }]
    }

    def __init__(self, page_path, start_date):
        """ GA initialization
        :param page_path: filter ga results by specified URL
        :param start_date: reports start date
        """
        # Global variables for all requests
        self.page_path = page_path
        self.start_date = start_date

        # Clean previous requests
        self.reports = []
        self.requests = []

        # GA AUTH
        google_analytics_key_file_path = 'ga-lifeloop.json'
        my_file = Path(google_analytics_key_file_path)
        if not my_file.is_file():
            data = {
                'type': TYPE,
                'project_id': CONF.get('google.analytics.project.id'),
                'private_key_id': CONF.get('google.analytics.private.key.id'),
                'private_key': '\n'.join(CONF.get('google.analytics.private.key').replace('"', '').split('\\n')),
                'client_email': CONF.get('google.analytics.client.email'),
                'client_id': CONF.get('google.analytics.client.id'),
                'auth_uri': AUTH_URI,
                'token_uri': TOKEN_URI,
                'auth_provider_x509_cert_url': AUTH_PROVIDER_X509_CERT_URL,
                'client_x509_cert_url': CONF.get('google.analytics.client.x509.cert.url')}
            with open(google_analytics_key_file_path, 'w') as outfile:
                json.dump(data, outfile)

        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            google_analytics_key_file_path,
            ['https://www.googleapis.com/auth/analytics.readonly'])

        self.view_id = CONF.get('google.analytics.view.id')
        self.analytics = discovery.build('analyticsreporting', 'v4',
                                         credentials=credentials)

    def add_report(self, attr_name):
        """ Add report for batchGet
        :return: report position in list
        """
        target = getattr(self, attr_name)

        request = {
            'viewId': self.view_id,
            'metrics': target['metrics'],
            'dimensions': target['dimensions'],
            'dimensionFilterClauses': {
                'filters': [{
                    'operator': 'EXACT',
                    'dimensionName': 'ga:pagePath',
                    'expressions': self.page_path
                }]
            },
            'dateRanges': [
                {'startDate': self.start_date, 'endDate': 'today'}
            ]
        }

        if target.get('orderBys'):
            request['orderBys'] = [target['orderBys']]
        if target.get('filters'):
            request['dimensionFilterClauses']['filters'].extend(
                target['filters'])

        self.requests.append(request)
        return len(self.requests) - 1

    def get(self):
        """ Send request to GA
        NOTE: Limit: 5 reports per request,
              all requests after 5 will be ignored
        :return: list of GA reports
        """
        try:
            response = self.analytics.reports().batchGet(body={
                'reportRequests': self.requests[:5]
            }).execute()
            if 'reports' in response:
                self.reports = response['reports']
        except (errors.BatchError, errors.HttpError, errors.Error) as e:
            LOG.exception('GA API ERROR: %s', str(e))
        return self.reports
