"""Template tags for form field rendering.

Usage in templates:
    {% load form_tags %}
    {% describedby_ids field as desc_ids %}
    {{ field|aria_describedby:desc_ids }}
"""
import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def describedby_ids(field):
    """Return space-separated IDs for aria-describedby based on what's present."""
    ids = []
    fid = field.id_for_label
    if field.help_text:
        ids.append(f"{fid}_helptext")
    if field.errors:
        ids.append(f"{fid}_error")
    return " ".join(ids)


@register.filter(name="aria_invalid")
def aria_invalid(bound_field):
    """Add aria-invalid="true" attribute to a rendered form widget if there are errors."""
    if getattr(bound_field, "errors", None):
        html = str(bound_field)
        if "aria-invalid=" not in html:
            html = re.sub(
                r"(<(?:input|select|textarea)\b)",
                r'\1 aria-invalid="true"',
                html,
                count=1,
            )
            return mark_safe(html)
    return bound_field


@register.filter(name="aria_describedby")
def aria_describedby(bound_field, describedby_id):
    """Add aria-describedby attribute to a rendered form widget."""
    if not describedby_id:
        return bound_field
    html = str(bound_field)
    if "aria-describedby=" in html:
        return bound_field
    html = re.sub(
        r"(<(?:input|select|textarea)\b)",
        rf'\1 aria-describedby="{describedby_id}"',
        html,
        count=1,
    )
    return mark_safe(html)
