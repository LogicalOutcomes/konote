"""Template tags and filters for the participant portal.

Usage in templates:
    {% load portal_tags %}
    {% portal_nav_active request "goals" %}
    {{ note.created_at|portal_date }}
    {{ program|portal_display_name }}
"""
from django import template
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

register = template.Library()

# Map section names to URL path prefixes for nav highlighting
_SECTION_PATHS = {
    "dashboard": "/my/",
    "goals": "/my/goals/",
    "progress": "/my/progress/",
    "my_words": "/my/my-words/",
    "milestones": "/my/milestones/",
    "journal": "/my/journal/",
    "message": "/my/message/",
    "discuss_next": "/my/discuss-next/",
    "settings": "/my/settings/",
    "safety": "/my/safety/",
}


@register.simple_tag
def portal_nav_active(request, section):
    """Return aria-current='page' if the current URL matches the section.

    For the dashboard, only matches the exact /my/ path.
    For other sections, matches if the path starts with the section prefix.

    Usage:
        <a href="{% url 'portal:goals_list' %}" {% portal_nav_active request "goals" %}>
            My Goals
        </a>
    """
    path = request.path
    section_path = _SECTION_PATHS.get(section, "")

    if not section_path:
        return ""

    # Dashboard is a special case — only exact match
    if section == "dashboard":
        if path == "/my/" or path == "/my":
            return mark_safe("aria-current='page'")
        return ""

    # Other sections match if path starts with the section prefix
    if path.startswith(section_path):
        return mark_safe("aria-current='page'")

    return ""


@register.filter
def portal_date(value):
    """Format a datetime for participant-friendly display.

    Returns a human-readable date like 'January 15, 2026'.
    Falls back gracefully if the value is None or not a date.

    Usage:
        {{ note.created_at|portal_date }}
    """
    if value is None:
        return ""

    try:
        # Use Django's locale-aware date formatting
        # 'N j, Y' gives "Jan. 15, 2026" in English; date_format respects
        # the active language for month names.
        return date_format(value, format="N j, Y")
    except (AttributeError, TypeError):
        return str(value)


@register.filter
def portal_display_name(program):
    """Return the portal-friendly display name for a programme.

    Prefers portal_display_name if set, falls back to translated_name
    (which handles English/French automatically).

    Usage:
        {{ program|portal_display_name }}
    """
    if program is None:
        return ""

    # Prefer portal_display_name if the field exists and has a value
    portal_name = getattr(program, "portal_display_name", None)
    if portal_name:
        return portal_name

    # Fall back to the language-aware translated_name property
    translated = getattr(program, "translated_name", None)
    if translated:
        return translated

    # Last resort — just the plain name
    return getattr(program, "name", "")
