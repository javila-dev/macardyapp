from django.apps import AppConfig


class McdSiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mcd_site'

    def ready(self):
        import mcd_site.signals  # noqa: F401
