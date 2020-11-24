""" TODO: Refactoring """

import datetime
import sqlalchemy as sa
from lifeloopweb.db import models
from lifeloopweb.ga_api import GA
from lifeloopweb import logging

LOG = logging.get_logger(__name__)


class Charts(object):
    sources = {
        'db': {
            'total_members',
            'new_members',
            'active_members',
            'video_sessions',
            'new_groups'
        },
        'ga': {
            'country',
            'sex_age',
            'visits'
        }
    }

    query_filter = {
        'db': '',
        'ga': ''
    }

    start_date = {
        'db': (datetime.datetime.now() - datetime.timedelta(weeks=4)).strftime('%Y-%m-%d'),
        'ga': (datetime.datetime.now() - datetime.timedelta(weeks=1)).strftime('%Y-%m-%d')
    }

    data = {}
    ga = None

    def __init__(self, org, duration=None):
        org_url = org.vanity_name if org.vanity_name else org.id
        self.query_filter['ga'] = '/%s' % org_url
        self.query_filter['db'] = org.id

        if duration:
            self.set_start_date(duration)

    @classmethod
    def set_start_date(cls, duration):
        if duration == 'day':
            kwarg = dict(days=1)
        elif duration == 'week':
            kwarg = dict(weeks=1)
        else:
            kwarg = dict(weeks=4)
        now = datetime.datetime.now()
        timedelta = datetime.timedelta(**kwarg)
        cls.start_date['db'] = cls.start_date['ga'] = (now - timedelta).strftime('%Y-%m-%d')

    def get(self, chart_type=None):
        data = {}
        if not chart_type or chart_type in self.sources['ga']:
            self.ga = GA('/%s' % self.query_filter['ga'], self.start_date['ga'])

        if chart_type:
            func_name = 'get_%s' % chart_type
            if hasattr(self, func_name):
                data = getattr(self, func_name)()
            else:
                LOG.info('Trying to get data for non-exists chart')
        else:
            data = {
                'total_members': self.get_total_members(),
                'new_members': self.get_new_members(),
                'active_members': self.get_active_members(),
                'video_sessions': self.get_video_sesssions(),
                'new_groups': self.get_new_groups()
            }
            data.update(self.ga_charts())
        return data

    def ga_charts(self):
        """ GET GA data for charts """
        ga = self.ga
        country_id = ga.add_report('COUNTRY')
        visits_id = ga.add_report('VISITS')
        male_id = ga.add_report('MALE')
        female_id = ga.add_report('FEMALE')
        ga.get()

        return {
            'country': self.get_country(country_id),
            'visits': self.get_visits(visits_id),
            'sex_age': self.get_sex_age(male_id, female_id)
        }

    @staticmethod
    def format_db_data(data, query):
        max_value = 0
        for year, month, day, count in query.all():
            if count > max_value:
                max_value = count
            data['labels'].append('%s-%s-%s' % (year, month, day))
            data['data'].append(count)
            if not data['total']:
                data['total'] += count
        if len(data['data']) == 1:
            data['labels'].append('Today')
            data['data'].append(0)
        data['max'] = round(max_value * 1.5)
        return data

    @staticmethod
    def format_sex_age_data(report, labels):
        total = 0
        rows = report['data'].get('rows')
        chart_data = []
        data = {}
        if rows:
            for ga_data in rows:
                key = ga_data['dimensions'][0]
                value = ga_data['metrics'][0]['values'][0]
                data[key] = int(value)
                total += data[key]
            for label in labels:
                chart_data.append(data[label] if data.get(label) else 0)
        return chart_data, total

    def get_country(self, report_id=None):
        ga = self.ga
        chart = {
            'labels': [],
            'data': []
        }

        if report_id:
            report = ga.reports[report_id]
        else:
            ga.add_report('COUNTRY')
            report = ga.get()[0]

        rows = report['data'].get('rows')
        if rows:
            for i, ga_country in enumerate(rows):
                label = ga_country['dimensions'][0]
                value = ga_country['metrics'][0]['values'][0]
                if i == 5:
                    chart['labels'].append('Other')
                    chart['data'].append(0)
                if i >= 5:
                    chart['data'][5] += int(value)
                else:
                    chart['data'].append(int(value))
                    chart['labels'].append(label)
        else:
            chart['data'].append(1)
            chart['labels'].append('No Sessions')
        return chart

    def get_visits(self, report_id=None):
        ga = self.ga
        chart = {
            'data': [[], []],
            'labels': [
                '01:00', '02:00', '03:00', '04:00', '05:00', '06:00',
                '07:00', '08:00', '09:00', '10:00', '11:00', '12:00'
            ]
        }
        visits_keys = ['00', '01', '02', '03', '04', '05',
                       '06', '07', '08', '09', '10', '11',
                       '12', '13', '14', '15', '16', '17',
                       '18', '19', '20', '21', '22', '23']
        if report_id:
            report = ga.reports[report_id]
        else:
            ga.add_report('VISITS')
            report = ga.get()[0]

        rows = report['data'].get('rows')

        visits = {}
        if rows:
            for ga_visits in rows:
                key = ga_visits['dimensions'][0]
                value = ga_visits['metrics'][0]['values'][0]
                if key not in visits:
                    visits[key] = 0
                visits[key] += int(value)
        data = [visits.get(label, 0) for label in visits_keys]
        chart['data'][0] = data[:12]
        chart['data'][1] = data[12:]
        return chart

    def get_sex_age(self, report_id=None, report2_id=None):
        """ SEX / AGE """
        ga = self.ga
        chart = {
            'data': [[], []],
            'total': [0, 0],
            'labels': ['18-24', '25-34', '35-44', '45-54', '55-64']
        }

        if report_id:
            reports = [ga.reports[report_id], ga.reports[report2_id]]
        else:
            ga.add_report('MALE')
            ga.add_report('FEMALE')
            ga.get()
            reports = ga.reports

        male_data, male_total = self.format_sex_age_data(reports[0], chart['labels'])
        chart['data'][0] = male_data
        female_data, female_total = self.format_sex_age_data(reports[1], chart['labels'])
        chart['data'][1] = female_data

        total = male_total + female_total
        if total:
            chart['total'][0] = format(male_total / total * 100, '.2f')
            chart['total'][1] = format(female_total / total * 100, '.2f')
        return chart

    def get_total_members(self):
        """ TOTAL MEMBERS """
        chart = {
            'labels': [],
            'data': [],
            'total': 0
        }

        cls = models.OrganizationMember
        date = cls.created_at

        year = sa.func.year(date)
        month = sa.func.month(date)
        day = sa.func.day(date)

        query = models.Session.query(
            year, month, day,
            sa.func.count(cls.id)
        ).filter(
            cls.organization_id == self.query_filter['db'],
            date.between(self.start_date['db'], datetime.datetime.now())
        ).order_by(
            date.desc()
        ).group_by(year, month, day)

        total_members = models.Session.query(cls).filter_by(
            organization_id=self.query_filter['db']
        ).count()

        chart['total'] = total_members
        return self.format_db_data(chart, query)

    def get_new_members(self):
        """ NEW MEMBERS """
        chart = {
            'labels': [],
            'data': [],
            'total': 0
        }

        cls = models.OrganizationMember
        date = cls.created_at

        year = sa.func.year(date)
        month = sa.func.month(date)
        day = sa.func.day(date)

        query = models.Session.query(
            year, month, day,
            sa.func.count(cls.id)
        ).filter(
            cls.organization_id == self.query_filter['db'],
            date.between(self.start_date['db'], datetime.datetime.now())
        ).group_by(year, month, day)

        return self.format_db_data(chart, query)

    def get_new_groups(self):
        """ NEW GROUPS """
        chart = {
            'labels': [],
            'data': [],
            'total': 0
        }

        cls = models.Group
        cls_related = models.OrganizationGroup

        date = cls.created_at
        year = sa.func.year(date)
        month = sa.func.month(date)
        day = sa.func.day(date)

        query = models.Session.query(
            year, month, day,
            sa.func.count(cls.id)
        ).join(
            cls_related
        ).filter(
            date.between(self.start_date['db'], datetime.datetime.now()),
            sa.and_(
                cls.archived_at.is_(None),
                cls_related.organization_id == self.query_filter['db']
            )
        ).group_by(year, month, day)

        return self.format_db_data(chart, query)

    @staticmethod
    def get_active_members():
        """ ACTIVE MEMBERS """
        data = {
            'labels': [],
            'data': [],
            'total': 0
        }
        return data

    @staticmethod
    def get_video_sesssions():
        """ VIDEO SESSIONS """
        data = {
            'labels': [],
            'data': [],
            'total': 0,
        }
        return data
