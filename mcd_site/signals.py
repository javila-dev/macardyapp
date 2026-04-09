from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from mcd_site.models import ensure_user_profile


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile_after_user_save(sender, instance, created, **kwargs):
    if created:
        ensure_user_profile(instance)


@receiver(user_logged_in)
def ensure_profile_after_login(sender, user, request, **kwargs):
    ensure_user_profile(user)
