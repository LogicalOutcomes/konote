"""Template tags and filters for the clients app."""

from django import template

register = template.Library()


@register.filter
def get_field(form, field_name):
    """Look up a form field by dynamic name.

    Usage: {{ form|get_field:"custom_42" }}
    """
    try:
        return form[field_name]
    except (KeyError, TypeError):
        return ""
