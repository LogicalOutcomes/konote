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


@register.filter(name="aria_describedby")
def aria_describedby(bound_field, describedby_id):
    """Add aria-describedby (and aria-invalid if errors exist) attribute to a rendered form widget."""
    html = str(bound_field)

    attributes = []
    if describedby_id and "aria-describedby=" not in html:
        attributes.append(f'aria-describedby="{describedby_id}"')

    if hasattr(bound_field, "errors") and bound_field.errors and "aria-invalid=" not in html:
        attributes.append('aria-invalid="true"')

    if not attributes:
        return bound_field

    attrs_str = " ".join(attributes)
    html = re.sub(
        r"(<(?:input|select|textarea)\b)",
        rf"\1 {attrs_str}",
        html,
        count=1,
    )
    return mark_safe(html)
