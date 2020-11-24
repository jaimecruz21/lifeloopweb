import cloudinary
from cloudinary import uploader, utils, api
from lifeloopweb import logging, config

CONF = config.CONF
LOG = logging.get_logger(__name__)


class CloudinaryHandler(object):

    def __init__(self, cloud_name=None, api_key=None, secret=None):
        self.cloud_name = cloud_name or CONF.get("cloudinary.cloud.name")
        self.api_key = api_key or CONF.get("cloudinary.api.key")
        self.secret = secret or CONF.get("cloudinary.secret")
        config_items = {'cloud_name': self.cloud_name,
                        'api_key': self.api_key,
                        'api_secret': self.secret}
        cloudinary.config(**config_items)

    def get_signature(self, params_to_sign):
        signature = utils.api_sign_request(params_to_sign, self.secret)
        return signature

    def upload(self, path_to_file):
        upload_preset = CONF.get('cloudinary.upload.preset')
        result = uploader.upload(
            path_to_file, tags=upload_preset)
        return result['secure_url']

    def delete(self, public_ids):
        # TODO: error handling
        api.delete_resources(public_ids)

    def delete_by_tag(self, tag):
        # TODO: error handling
        api.delete_resources_by_tag(tag)

    @classmethod
    def cloudinary_elements(cls):
        env = CONF.get('environment')
        cloudinary_api_key = CONF.get('cloudinary.api.key')
        cloudinary_cloud_name = CONF.get('cloudinary.cloud.name')
        cloudinary_upload_preset = CONF.get('cloudinary.upload.preset')
        return {'env': env,
                'cloudinary_api_key': cloudinary_api_key,
                'cloudinary_cloud_name': cloudinary_cloud_name,
                'cloudinary_upload_preset': cloudinary_upload_preset}
