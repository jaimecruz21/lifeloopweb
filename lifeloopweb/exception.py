class LifeloopException(Exception):
    def __init__(self, **keys):
        super().__init__(self.message % keys)

    @property
    def message(self):
        raise NotImplementedError('Message not set!')


class InvalidProductionConfig(LifeloopException):
    message = ("A development-only configuration was attempted to be "
               "used in production: %(msg)s")


class ConfigKeyNotFound(LifeloopException):
    message = ("The requested key '%(key)s' does not exist in the "
               "application configuration")


class ConfigConflict(LifeloopException):
    message = ("The requested key '%(key)s' already exists in the config "
               "and has value '%(value)s'")


class InvalidConfigValue(LifeloopException):
    message = ("The value '%(value)s' for config variable '%(key)s' "
               "is invalid")


class ModelUnknownAttribute(LifeloopException):
    message = "Model '%(model)s' has no field named '%(attr)s'"


class InvalidShardId(LifeloopException):
    message = "Shard IDs '%(shard_id)s's must be 0 <= shard_id < %(max_shard)s"


class InvalidTokenVersion(LifeloopException):
    message = "Version '%(version)s' is not a supported token version"


class MalformedTokenByMissingField(LifeloopException):
    message = "Token is missing field '%(field)s'"


class MalformedToken(LifeloopException):
    message = "Token is malformed"


class UserAlreadyExists(LifeloopException):
    message = "User already exists for email address '%(email)s'"


class UserTimezoneMissing(LifeloopException):
    message = "User does not have a timezone assigned"


class GroupNotFound(LifeloopException):
    message = "Group not found"


class OrganizationNotFound(LifeloopException):
    message = "Organization Not Found"


class InvalidEmail(LifeloopException):
    message = "Invalid Email"


class InvalidFileExtensionException(LifeloopException):
    message = ("Invalid file extension '%(ext)s'. "
               "Allowed extensions are %(exts)s")


class FileAlreadyExists(LifeloopException):
    message = ("File %(filename)s already exists."
               "  Please use a different name.")


class MethodNotExists(LifeloopException):
    message = ''

    def __init__(self, instance, method):
        self.message = "%(instance)s.%(method)s() method not implemented"
        super().__init__(instance=type(instance).__name__, method=method)
