import requests

import tinys3
from werkzeug.utils import secure_filename

from lifeloopweb import config, exception as exc, logging

LOG = logging.get_logger(__name__)
CONF = config.CONF


class FileHandler(object):
    allowed_file_extensions = CONF.get_array('allowed.file.extensions')
    allowed_image_extensions = CONF.get_array('allowed.image.extensions')
    ALLOWED_EXTENSIONS = allowed_file_extensions + allowed_image_extensions

    def __init__(self, lifeloop_file):
        self.lifeloop_file = lifeloop_file

    def validate(self):
        if not self.allowed_file:
            raise exc.InvalidFileExtensionException(
                ext=self.file_extension,
                exts=', '.join(self.ALLOWED_EXTENSIONS))

    def save(self, override=False):
        raise NotImplementedError("Parent FileHandler has no implementation")

    @property
    def allowed_file(self):
        return ('.' in self.new_filename and
                self.file_extension in self.ALLOWED_EXTENSIONS)

    @property
    def file_extension(self):
        return self.lifeloop_file.filename.rsplit('.', 1)[1].lower()


class S3FileHandler(FileHandler):
    AWS_ACCESS_KEY = CONF.get('aws.access.key.id')
    AWS_SECRET_KEY = CONF.get('aws.secret.access.key')
    AWS_BUCKET_NAME = CONF.get('aws.bucket.name')

    def __init__(self, document, new_name=None):
        super(S3FileHandler, self).__init__(document)
        self.url = ''
        self.conn = tinys3.Connection(
            self.AWS_ACCESS_KEY,
            self.AWS_SECRET_KEY,
            default_bucket=self.AWS_BUCKET_NAME)
        if new_name:
            self.new_filename = ("{}.{}".format(
                secure_filename(new_name), self.file_extension))
        else:
            self.new_filename = secure_filename(self.lifeloop_file.filename)

    @property
    def filename(self):
        return self.new_filename

    def exists(self, key):
        exists = False
        try:
            response = self.conn.get(key)
            if response and response.status_code == 200:
                exists = True
        except requests.exceptions.HTTPError as e:
            LOG.exception("Found an existing item with that key in"
                          " or another error. %s", e.response.text)
            return False
        return exists

    def save(self, override=False):
        self.validate()
        if not override:
            if self.exists(self.new_filename):
                LOG.debug("File '%s' already exists in S3 bucket '%s'",
                          self.new_filename,
                          self.AWS_BUCKET_NAME)
                raise exc.FileAlreadyExists(filename=self.new_filename)
        LOG.debug(
            "Saving file to S3 with key '%s' in bucket '%s'",
            self.new_filename, self.AWS_BUCKET_NAME)
        response = self.conn.upload(self.new_filename, self.lifeloop_file)
        if response and response.status_code == 200:
            return response.url
        else:
            raise Exception("FIle not saved to S3: {}".format(self.filename))

    @classmethod
    def delete(cls, key):
        conn = tinys3.Connection(
            cls.AWS_ACCESS_KEY,
            cls.AWS_SECRET_KEY,
            default_bucket=cls.AWS_BUCKET_NAME)
        conn.delete(key, bucket=cls.AWS_BUCKET_NAME)


class InvalidFileExtensionException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class FileAlreadyExists(Exception):

    def __init__(self, message):
        super().__init__(message)
        self.message = message
