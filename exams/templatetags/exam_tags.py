from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract_from(value, arg):
    try:
        return float(arg) - float(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def attribute(obj, attr):
    """Gets an attribute of an object dynamically."""
    return getattr(obj, attr, '')
