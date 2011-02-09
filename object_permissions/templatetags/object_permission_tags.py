from django.contrib.auth.models import User
from django.template import Library

from object_permissions.models import Group
from object_permissions.registration import get_user_perms

register = Library()


@register.filter
def permissions(user, object):
    """
    Returns the list of permissions a user has on an object
    """
    if user:
        return user.get_perms(object)
    return []


@register.filter
def group_admin(user):
    """
    Returns True or False based on if the user is an admin for any Groups
    """
    return user.is_superuser or user.has_any_perms(Group, ['admin'])


@register.filter
def class_name(cls):
    """
    Returns name of class for a class object
    """
    return cls.__name__


@register.filter
def is_user(obj):
    """
    Returns True if obj is a user
    """
    return isinstance(obj, (User,))