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
    
@register.filter
def current_date(value):
    return timezone.now().date()

@register.filter
def get_plan_description(plan_value):
    return {
        'Daily': '500 - Umunsi wose',
        'Weekly': '2000 - Icyumweru cyose',
        'Monthly': '5000 - Ukwezi kose',
        'Super': '15000 - Rihoraho',
    }.get(plan_value, '')

@register.filter
def get_plan_price(value):
    return {
        'Daily': '500',
        'Weekly': '2000',
        'Monthly': '5000',
        'Super': '15000',
    }.get(value, '')

@register.filter
def choice_class(answer, choice):
    """
    Returns the appropriate CSS class based on the answer and choice.
    """
    if answer.selected_choice_number == choice['id'] and not choice['is_correct']:
        return "border-danger border bg-danger text-white"
    elif choice['is_correct']:
        return "border-success border bg-success text-white"
    return ""

@register.filter
def choice_condition(answer, choice):
    """
    Returns True if the selected choice is incorrect, False otherwise.
    """
    return answer.selected_choice_number == choice['id'] and not choice['is_correct']

@register.filter
def to_int(value):
    """
    Converts a value to an integer.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def has_attribute(obj, attr):
    """
    Checks if the given object has the specified attribute.
    """
    return hasattr(obj, attr)

@register.filter
def all(iterable, attr):
    """
    Custom filter to check if all elements in an iterable have a specific attribute value.
    Example: {% if choices|all:"type=image" %}
    """
    try:
        key, value = attr.split("=")
        result = all(item.get(key) == value for item in iterable)
        print(f"Checking if all elements in {iterable} have {key}={value}: {result}")  # Debug output
        return result
    except ValueError:
        return False
