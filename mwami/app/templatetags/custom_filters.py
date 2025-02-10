from django import template
from django.utils import timezone
from django.utils import timezone



register = template.Library()

@register.filter
def get(dictionary, key):
    """
    Returns the value for the given key from a dictionary.
    The key is converted to a string because session keys are stored as strings.
    """
    try:
        return dictionary.get(str(key))
    except (AttributeError, TypeError):
        return ''

@register.filter
def range_to_21(value):
    return range(value, 22)  # 6 AM to 9 PM (21:00)
