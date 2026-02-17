"""Plain-language interpretations of insight data.

Pure functions that take structured insight data and return short,
translatable sentences for display below charts. No AI API calls —
just data-driven template strings.

Audience: nonprofit staff (coordinators, coaches, counsellors),
not analysts or developers.
"""
from django.utils.translation import gettext as _


def interpret_progress_trend(descriptor_trend):
    """Interpret the descriptor trend (first vs last month).

    Args:
        descriptor_trend: list of dicts with keys:
            month, harder, holding, shifting, good_place (all percentages)

    Returns:
        str or "" if not enough data.
    """
    if not descriptor_trend:
        return ""
    if len(descriptor_trend) < 2:
        return _("With only one month of data, it is too early to spot trends.")

    first = descriptor_trend[0]
    last = descriptor_trend[-1]

    good_start = first["good_place"]
    good_end = last["good_place"]
    good_change = good_end - good_start

    harder_start = first["harder"]
    harder_end = last["harder"]
    harder_change = harder_end - harder_start

    parts = []

    # "in a good place" movement
    if good_change > 5:
        parts.append(
            _("the share of participants 'in a good place' rose from "
              "%(start)s%% to %(end)s%%")
            % {"start": good_start, "end": good_end}
        )
    elif good_change < -5:
        parts.append(
            _("the share of participants 'in a good place' dropped from "
              "%(start)s%% to %(end)s%%")
            % {"start": good_start, "end": good_end}
        )

    # "harder right now" movement
    if harder_change < -5:
        parts.append(
            _("'harder right now' dropped from %(start)s%% to %(end)s%%")
            % {"start": harder_start, "end": harder_end}
        )
    elif harder_change > 5:
        parts.append(
            _("'harder right now' rose from %(start)s%% to %(end)s%%")
            % {"start": harder_start, "end": harder_end}
        )

    if parts:
        changes = _(" and ").join(parts)
        return (
            _("Over this period, %(changes)s.")
            % {"changes": changes}
        )

    return _("Progress levels have been relatively stable over this period.")


def interpret_engagement(engagement_raw):
    """Interpret the engagement distribution.

    Args:
        engagement_raw: dict of raw DB keys to percentages,
            e.g. {"engaged": 45.0, "valuing": 27.0, "guarded": 15.0, ...}

    Returns:
        str or "" if no data.
    """
    if not engagement_raw:
        return ""

    positive_pct = round(
        engagement_raw.get("engaged", 0) + engagement_raw.get("valuing", 0)
    )

    if positive_pct >= 60:
        return (
            _("%(pct)s%% of participants are actively engaged or finding "
              "value in their program.")
            % {"pct": positive_pct}
        )
    elif positive_pct >= 40:
        return (
            _("%(pct)s%% of participants are actively engaged. There may "
              "be room to explore what would help others connect more.")
            % {"pct": positive_pct}
        )
    else:
        return (
            _("About %(pct)s%% of participants are actively engaged. "
              "Considering what barriers might be affecting engagement "
              "could be helpful.")
            % {"pct": positive_pct}
        )


def interpret_descriptor_snapshot(descriptor_trend):
    """Interpret the current descriptor distribution using the latest trend data.

    Uses the last entry in descriptor_trend (which has stable raw keys)
    rather than descriptor_distribution (which has translated label keys).

    Args:
        descriptor_trend: list of dicts with month/harder/holding/shifting/good_place.

    Returns:
        str or "" if no data.
    """
    if not descriptor_trend:
        return ""

    latest = descriptor_trend[-1]

    # Find the dominant category
    categories = {
        "good_place": (_("in a good place"), latest["good_place"]),
        "shifting": (_("something's shifting"), latest["shifting"]),
        "holding": (_("holding steady"), latest["holding"]),
        "harder": (_("harder right now"), latest["harder"]),
    }

    dominant_key = max(categories, key=lambda k: categories[k][1])
    dominant_label, dominant_pct = categories[dominant_key]

    if dominant_pct < 10:
        return ""  # No meaningful dominant group

    return (
        _("Right now, the largest group of participants (%(pct)s%%) "
          "are '%(label)s'.")
        % {"pct": dominant_pct, "label": dominant_label}
    )


def interpret_suggestions(suggestion_total, suggestion_important_count):
    """Interpret the suggestion summary.

    Args:
        suggestion_total: int — total suggestions recorded.
        suggestion_important_count: int — count of important + urgent suggestions.

    Returns:
        str or "" if zero.
    """
    if not suggestion_total:
        return ""

    if suggestion_important_count > 0:
        return (
            _("%(total)s suggestions were recorded, including %(important)s "
              "marked as important or urgent.")
            % {"total": suggestion_total, "important": suggestion_important_count}
        )

    return (
        _("%(total)s suggestions were recorded this period.")
        % {"total": suggestion_total}
    )


def interpret_client_trend(descriptor_trend):
    """Client-level variant — uses "their" instead of "participants".

    Args:
        descriptor_trend: list of dicts with month/harder/holding/shifting/good_place.

    Returns:
        str or "" if not enough data.
    """
    if not descriptor_trend:
        return ""
    if len(descriptor_trend) < 2:
        return _("With only one month of data, it is too early to spot trends.")

    first = descriptor_trend[0]
    last = descriptor_trend[-1]

    good_change = last["good_place"] - first["good_place"]
    harder_change = last["harder"] - first["harder"]

    if good_change > 5:
        return (
            _("Their recent notes show a shift towards feeling "
              "'in a good place' — up from %(start)s%% to %(end)s%%.")
            % {"start": first["good_place"], "end": last["good_place"]}
        )
    elif harder_change > 5:
        return (
            _("Their recent notes show more sessions feeling "
              "'harder right now' — up from %(start)s%% to %(end)s%%.")
            % {"start": first["harder"], "end": last["harder"]}
        )
    elif good_change < -5:
        return (
            _("The share of notes where they felt 'in a good place' "
              "decreased from %(start)s%% to %(end)s%% over this period.")
            % {"start": first["good_place"], "end": last["good_place"]}
        )

    return _("Their progress has been relatively steady over this period.")
