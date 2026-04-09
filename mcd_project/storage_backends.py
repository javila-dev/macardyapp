from django.conf import settings
from django.utils.encoding import filepath_to_uri
from storages.backends.s3boto3 import S3Boto3Storage


class PublicMediaStorage(S3Boto3Storage):
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False

    def url(self, name, parameters=None, expire=None, http_method=None):
        base_url = getattr(settings, 'PERSISTENT_MEDIA_BASE_URL', settings.MEDIA_URL)
        if not name:
            return base_url
        normalized = str(name).replace('\\', '/').lstrip('/')
        return f"{base_url}{filepath_to_uri(normalized)}"
