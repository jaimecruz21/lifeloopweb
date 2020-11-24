# pylint: disable=protected-access
import mock

import pytest

from lifeloopweb import lifeloopweb_app
from lifeloopweb.db import utils
import tests


class TestUnitBase(tests.TestBase):
    """
    Unit testing base class

    Implemented as a standalone module to fix an issue where lifeloopweb_app
    gets imported before the environment variables can be overridden."""

    def mock_for(self, model_kls, **fields):
        if not hasattr(model_kls, "__table__"):
            raise Exception("'{}' does not appear to be a SQLAlchemy model")

        fields_in_model = set([])

        for column in model_kls.__table__.columns:
            fields_in_model.add(column.name)

        fields_to_set = set(fields.keys())
        missing_in_fields = fields_in_model - fields_to_set
        missing_in_model = fields_to_set - fields_in_model
        errs = []
        if missing_in_model:
            errs.append("The following fields do not match those in the "
                        "model: {}".format(missing_in_model))
        if missing_in_fields:
            errs.append("The model expects the following fields to "
                        "be set for mocking: {}".format(missing_in_fields))
        if errs:
            raise Exception("Error in mocking model '{}': {}".format(model_kls,
                                                                     '\n'.join(errs)))
        return model_kls(**fields)

    @pytest.fixture()
    def app(self):
        lifeloopweb_app.app.testing = True
        lifeloopweb_app.app.config["PRESERVE_CONTEXT_ON_EXCEPTION"] = True
        lifeloopweb_app.app.login_manager._login_disabled = True

        class MockTransaction(object):
            def __init__(self):
                self._add_models = []
                self._delete_models = []

            @property
            def add_models(self):
                return self._add_models

            @property
            def delete_models(self):
                return self._delete_models

            @classmethod
            def __call__(cls):
                pass

            def add(self, model):
                self._add_models.append(model)

            def delete(self, model):
                self._delete_models.append(model)

        mock_transaction = MockTransaction()

        class MockContext(object):
            @property
            def mock_transaction(self):
                return mock_transaction

            @classmethod
            def __enter__(cls, *args, **kwargs):
                return mock_transaction

            @classmethod
            def __exit__(cls, *args, **kwargs):
                pass

        def mock_redirect(_url):
            return ("Ok", "200")

        with mock.patch("lifeloopweb.db.models.transaction", MockContext), \
             mock.patch("flask.redirect", mock_redirect):
            yield lifeloopweb_app.app.test_client()

        lifeloopweb_app.app.testing = False

    def url_for(self, sub_route):
        return "{}{}".format(self.APP_PREFIX, sub_route)

    def generate_guid(self):
        return utils.generate_guid()
