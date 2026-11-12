from django import template

from users.permissions import get_user_access

register = template.Library()


@register.simple_tag
def inventory_navigation(user):
    return get_user_access(user)
