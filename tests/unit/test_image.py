from lifeloopweb import cloudinary

import tests


class TestImage(tests.TestBase):
    def test_get_signature(self):
        params_to_sign = {"public_id": "sample_image",
                          "timestamp": "1315060510"}
        signature = cloudinary.CloudinaryHandler().get_signature(
            params_to_sign)
        assert signature == "6201833e0ac13c1175b31ed714b8377ce4104958"
