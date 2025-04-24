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
        'Daily': [
            ('⏱️', 'Rimara Umunsi wose'),
            ('📝', 'Ukora ibizamini byose ushaka'),
            ('🤝', 'Uhabwa ubufasha igihe cyose'),
        ],
        'Weekly': [
            ('📆', 'Rimara Icyumweru Cyose'),
            ('📝', 'Ukora ibizamini byose ushaka'),
            ('🤝', 'Uhabwa ubufasha igihe cyose'),
        ],
        'Monthly': [
            ('🗓️', 'Rimara Ukwezi kose'),
            ('📝', 'Ukora ibizamini byose ushaka'),
            ('🤝', 'Uhabwa ubufasha bwose ushaka'),
        ],
    }.get(plan_value, [])


@register.filter
def get_old_price(value):
    return {
        # 'Daily': '1000 RWF',
        'Weekly': '4000 RWF',
        'Monthly': '10000 RWF',
        }.get(value, '')

@register.filter
def get_plan_price(value):
    return {
        'Daily': '1000',
        'Weekly': '2000',
        'Monthly': '5000',
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


@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})

@register.filter
def get_id(questions, index):
    try:
        return questions[index - 1].id
    except:
        return None

@register.filter
def get_question_id(q_num, questions):
    """Takes a question number and list of questions, returns the question's ID."""
    try:
        return questions[int(q_num)-1].id
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def is_answered(q_num, args):
    """Check if a question number has been answered."""
    questions, answers = args
    try:
        question_id = questions[int(q_num) - 1].id
        return str(question_id) in answers
    except (IndexError, ValueError, TypeError):
        return False
@register.filter
def isin(value, container):
    """Check if value is in container."""
    return str(value) in container