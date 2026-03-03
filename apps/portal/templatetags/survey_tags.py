"""Template tags for portal survey forms."""
from django import template

register = template.Library()


@register.filter
def bilingual(en_value, fr_value):
    """Return FR text when language is French and FR text exists, else EN."""
    from django.utils.translation import get_language
    if get_language() == "fr" and fr_value:
        return fr_value
    return en_value


@register.filter
def partial_value(question_pk, partial_answers):
    """Look up a question's saved value from partial_answers dict."""
    if not partial_answers or not question_pk:
        return ""
    return partial_answers.get(int(question_pk), "")


@register.filter
def in_multi_value(opt_value, saved_value):
    """Check if opt_value is in a semicolon-separated saved_value string."""
    if not saved_value:
        return False
    return str(opt_value) in str(saved_value).split(";")
