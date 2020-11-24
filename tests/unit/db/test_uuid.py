import uuid

import pytest

from lifeloopweb.db import utils
from lifeloopweb import exception
import tests


class TestUUID(tests.TestBase):
    def test_generate_uuid(self):
        base_uuid = "12345678-9ABC-DEF0-1234-56789ABCDEF0"
        expected_uuid = uuid.UUID("EF09ABC1-2345-678D-1234-56789ABCD000")
        output_uuid = utils.generate_guid(base_uuid=base_uuid)
        assert output_uuid == expected_uuid

    def test_generate_uuid_other_shard(self):
        base_uuid = "12345678-9ABC-DEF0-1234-56789ABCDEF0"
        expected_uuid = uuid.UUID("EF09ABC1-2345-678D-1234-56789ABCDFFF")
        output_uuid = utils.generate_guid(shard=4095, base_uuid=base_uuid)
        assert output_uuid == expected_uuid

    def test_generate_uuid_bad_shard(self):
        base_uuid = "12345678-9ABC-DEF0-1234-56789ABCDEF0"
        bad_shard = utils.MAX_SHARD + 1
        with pytest.raises(exception.InvalidShardId):
            utils.generate_guid(shard=bad_shard, base_uuid=base_uuid)

    def test_generate_actual_uuid_parses_correctly(self):
        with self.not_raises():
            utils.generate_guid()
