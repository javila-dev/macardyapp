from django import template

register = template.Library()

@register.filter
def has_perm(user_profile, perm):
    return user_profile.has_permission(perm)