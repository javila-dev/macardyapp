from django.conf import settings
from django.utils.encoding import filepath_to_uri
from storages.backends.s3boto3 import S3Boto3Storage


class PublicMediaStorage(S3Boto3Storage):
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False

    def url(self, name, parameters=None, expire=None, http_method=None):
        if not name:
            return settings.MEDIA_URL
        normalized = str(name).replace('\\', '/').lstrip('/')
        return f"{settings.MEDIA_URL}{filepath_to_uri(normalized)}"
