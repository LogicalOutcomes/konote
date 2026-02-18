"""Theme matching engine for Suggestion Themes automation.

Tier 1: Lightweight keyword matching on note save — no AI, no network.
Tier 2: AI-powered theme identification during Outcome Insights generation.
"""
import logging
import re

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Common English stopwords excluded from keyword matching.
STOPWORDS = frozenset({
    "the", "a", "an", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "it", "its", "i", "me",
    "my", "we", "our", "you", "your", "he", "she", "they", "them", "this",
    "that", "these", "those", "and", "but", "or", "nor", "not", "so",
    "very", "just", "about", "up", "more", "also", "like", "want", "need",
    "think", "really", "much", "get", "all", "some", "any", "each",
    "every", "such", "what", "which", "who", "when", "where", "how",
    "than", "too", "only", "own", "same", "here", "there", "thing",
    "things", "one", "two", "many", "make", "know", "good", "well",
    "been", "come", "came", "time", "way", "day", "said", "see", "lot",
})

_WORD_RE = re.compile(r"[a-z]+")


def _extract_content_words(text):
    """Extract meaningful content words from text (lowered, no stopwords)."""
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _check_privacy_gate(program):
    """Return True if theme operations are allowed for this program.

    Mirrors the privacy gate in collect_quotes() — programs with fewer
    than 15 enrolled participants don't get auto-themes to prevent
    re-identification risk.
    """
    if getattr(settings, "DEMO_MODE", False):
        return True

    from apps.clients.models import ClientProgramEnrolment
    from apps.reports.insights import MIN_PARTICIPANTS_FOR_QUOTES

    participant_count = (
        ClientProgramEnrolment.objects.filter(
            program=program, status="enrolled",
        )
        .values("client_file_id")
        .distinct()
        .count()
    )
    if participant_count < MIN_PARTICIPANTS_FOR_QUOTES:
        logger.info(
            "Theme privacy gate: program %s has %d participants (minimum %d)",
            program.name, participant_count, MIN_PARTICIPANTS_FOR_QUOTES,
        )
        return False
    return True


# ── Tier 1: Lightweight auto-link on note save ─────────────────────

def try_auto_link_suggestion(note):
    """Check if a note's suggestion matches any active theme by keywords.

    Called after note save. Fast, no AI, no network call.
    Links the note to matching themes with auto_linked=True.

    Args:
        note: ProgressNote instance with participant_suggestion and
              suggestion_priority already set.

    Returns:
        list of SuggestionTheme instances that were newly linked.
    """
    from .models import SuggestionLink, SuggestionTheme, recalculate_theme_priority

    if not note.participant_suggestion or not note.suggestion_priority:
        return []

    program = note.author_program
    if not program:
        return []

    if not _check_privacy_gate(program):
        return []

    suggestion_words = _extract_content_words(note.participant_suggestion)
    if len(suggestion_words) < 2:
        return []

    active_themes = SuggestionTheme.objects.active().filter(program=program)
    if not active_themes.exists():
        return []

    linked_themes = []
    for theme in active_themes:
        theme_text = f"{theme.name} {theme.description} {theme.keywords}"
        theme_words = _extract_content_words(theme_text)

        overlap = suggestion_words & theme_words
        if len(overlap) >= 2:
            _, created = SuggestionLink.objects.get_or_create(
                theme=theme,
                progress_note=note,
                defaults={"auto_linked": True, "linked_by": None},
            )
            if created:
                linked_themes.append(theme)

    for theme in linked_themes:
        recalculate_theme_priority(theme)

    return linked_themes


# ── Tier 2: AI-powered theme identification ─────────────────────────

def process_ai_themes(ai_themes, quote_source_map, program):
    """Create or update SuggestionTheme records from AI response.

    Called after Outcome Insights generation. Uses the ephemeral
    quote_source_map (scrubbed_text → note_id) to link themes back
    to source ProgressNote records. The map is never persisted.

    Args:
        ai_themes: list of dicts from AI response, each with:
            name, description, category, keywords, supporting_quotes
        quote_source_map: dict {scrubbed_text: note_id} — ephemeral.
        program: Program instance.
    """
    from .models import SuggestionLink, SuggestionTheme, recalculate_theme_priority

    if not _check_privacy_gate(program):
        return

    # Only theme program-design suggestions, not operational ones.
    design_themes = [
        t for t in ai_themes
        if isinstance(t, dict) and t.get("category") == "program_design"
    ]

    if not design_themes:
        return

    with transaction.atomic():
        for ai_theme in design_themes:
            theme_name = str(ai_theme.get("name", "")).strip()[:200]
            if not theme_name:
                continue

            # Try case-insensitive match against existing themes.
            theme = (
                SuggestionTheme.objects.filter(
                    program=program,
                    name__iexact=theme_name,
                ).first()
            )

            if theme is None:
                theme = SuggestionTheme.objects.create(
                    program=program,
                    name=theme_name,
                    description=str(ai_theme.get("description", ""))[:500],
                    source="ai_generated",
                    created_by=None,
                    keywords=", ".join(ai_theme.get("keywords", []))[:500],
                )
            else:
                # Update keywords if theme has none and AI provided them.
                if not theme.keywords and ai_theme.get("keywords"):
                    theme.keywords = ", ".join(ai_theme["keywords"])[:500]
                    theme.save(update_fields=["keywords", "updated_at"])

            # Link supporting quotes via quote_source_map.
            for quote_text in ai_theme.get("supporting_quotes", []):
                if not isinstance(quote_text, str):
                    continue
                note_id = _find_note_id(quote_text, quote_source_map)
                if note_id:
                    SuggestionLink.objects.get_or_create(
                        theme=theme,
                        progress_note_id=note_id,
                        defaults={"auto_linked": True, "linked_by": None},
                    )

            recalculate_theme_priority(theme)


def _find_note_id(quote_text, quote_source_map):
    """Look up a quote in the source map, using substring matching.

    The AI may return a truncated or slightly trimmed version of the
    original scrubbed quote. Try exact match first, then substring.
    """
    # Exact match.
    if quote_text in quote_source_map:
        return quote_source_map[quote_text]

    # Substring match: AI quote is contained in an original, or vice versa.
    for scrubbed, note_id in quote_source_map.items():
        if quote_text in scrubbed or scrubbed in quote_text:
            return note_id

    return None
