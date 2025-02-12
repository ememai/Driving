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

@register.filter
def letter(index):
    """
    Convert an integer index (starting at 0) to a letter.
    For example, 0 -> A, 1 -> B, 2 -> C, etc.
    """
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    try:
        index = int(index)
        # If index is out-of-range, return an empty string.
        return letters[index] if 0 <= index < len(letters) else ""
    except (ValueError, TypeError):
        return ""

@register.filter
def percentage(value, total):
    """
    Returns the percentage (as a float) of value over total.
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 0
        return (value / total) * 100
    except (ValueError, TypeError):
        return 0