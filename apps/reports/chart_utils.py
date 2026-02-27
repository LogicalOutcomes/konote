"""Server-side chart generation for PDF reports using matplotlib.

Generates bar charts and line charts as base64-encoded PNG images suitable
for embedding in HTML via data URIs.  WeasyPrint renders these in PDFs.

Colour palette follows WCAG 2.2 AA contrast requirements:
- All chart colours have at least 3:1 contrast against white backgrounds
- Patterns/labels supplement colour so information is not colour-dependent
- Text labels meet 4.5:1 contrast for normal text
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Attempt to import matplotlib; charts are degraded gracefully if missing
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend — no display needed
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not installed; PDF charts will be unavailable")


# Accessible colour palette — all meet WCAG 2.2 AA 3:1 contrast on white.
# Chosen for distinguishability across common colour-vision deficiencies.
CHART_COLOURS = [
    "#3176aa",  # Teal (brand primary) — 5.1:1 contrast
    "#b35900",  # Burnt orange — 4.6:1 contrast
    "#5b21b6",  # Deep purple — 7.3:1 contrast
    "#0369a1",  # Ocean blue — 4.7:1 contrast
    "#9d174d",  # Berry — 6.2:1 contrast
    "#065f46",  # Forest green — 6.8:1 contrast
    "#92400e",  # Amber brown — 4.5:1 contrast
    "#6b21a8",  # Violet — 6.9:1 contrast
]

# Hatch patterns for accessibility — distinguish bars without relying on colour
HATCH_PATTERNS = ["", "//", "\\\\", "xx", "..", "++", "oo", "**"]

# Chart text colour — 12.6:1 contrast on white
CHART_TEXT_COLOUR = "#1a202c"

# Chart dimensions (inches) — fits within PDF letter page with margins
CHART_WIDTH = 6.5
CHART_HEIGHT = 3.5


def is_chart_available() -> bool:
    """Check if chart generation is available."""
    return MATPLOTLIB_AVAILABLE


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def generate_bar_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    ylabel: str = "",
    value_suffix: str = "",
) -> str | None:
    """Generate a bar chart comparing values across categories.

    Suitable for single-period demographic comparisons (e.g., metric
    values by age group).

    Args:
        labels: Category labels (e.g., ["Age 13-17", "Age 18-24", "Age 25+"]).
        values: Numeric values for each category.
        title: Chart title.
        ylabel: Y-axis label.
        value_suffix: Suffix for value labels (e.g., "%" for percentages).

    Returns:
        Base64 data URI string, or None if chart generation unavailable.
    """
    if not MATPLOTLIB_AVAILABLE or not labels or not values:
        return None

    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT))

    colours = [CHART_COLOURS[i % len(CHART_COLOURS)] for i in range(len(labels))]
    hatches = [HATCH_PATTERNS[i % len(HATCH_PATTERNS)] for i in range(len(labels))]

    bars = ax.bar(labels, values, color=colours, edgecolor=CHART_TEXT_COLOUR,
                  linewidth=0.5)

    # Apply hatch patterns for accessibility
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    # Add value labels on top of each bar
    for bar, val in zip(bars, values):
        display_val = f"{val}{value_suffix}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(values) * 0.02 if max(values) > 0 else 0.1),
            display_val,
            ha="center", va="bottom",
            fontsize=9, color=CHART_TEXT_COLOUR, fontweight="bold",
        )

    if title:
        ax.set_title(title, fontsize=12, color=CHART_TEXT_COLOUR,
                      fontweight="bold", pad=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=CHART_TEXT_COLOUR)

    ax.tick_params(axis="x", labelsize=9, labelcolor=CHART_TEXT_COLOUR)
    ax.tick_params(axis="y", labelsize=9, labelcolor=CHART_TEXT_COLOUR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#d1d5db")
    ax.spines["bottom"].set_color("#d1d5db")

    # Ensure y-axis starts at 0
    ax.set_ylim(bottom=0)

    # Add some top margin for value labels
    if values and max(values) > 0:
        ax.set_ylim(top=max(values) * 1.15)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_line_chart(
    period_labels: list[str],
    series: list[dict[str, Any]],
    title: str = "",
    ylabel: str = "",
    value_suffix: str = "",
) -> str | None:
    """Generate a line chart showing trends over multiple periods.

    Suitable for multi-period trend visualisation (e.g., metric values
    over the last 4 quarters).

    Args:
        period_labels: Time period labels (e.g., ["Q1", "Q2", "Q3", "Q4"]).
        series: List of series dicts:
            [{"label": "All Participants", "values": [3.2, 3.5, 3.8, 4.0]}, ...]
        title: Chart title.
        ylabel: Y-axis label.
        value_suffix: Suffix for value labels (e.g., "%" for percentages).

    Returns:
        Base64 data URI string, or None if chart generation unavailable.
    """
    if not MATPLOTLIB_AVAILABLE or not period_labels or not series:
        return None

    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT))

    markers = ["o", "s", "D", "^", "v", "P", "X", "*"]

    for i, s in enumerate(series):
        colour = CHART_COLOURS[i % len(CHART_COLOURS)]
        marker = markers[i % len(markers)]
        vals = s["values"]

        # Handle series shorter than period labels (pad with None)
        padded = vals + [None] * (len(period_labels) - len(vals))

        ax.plot(
            period_labels, padded,
            color=colour, marker=marker, markersize=7,
            linewidth=2, label=s["label"],
        )

        # Add value labels at each point
        for j, val in enumerate(padded):
            if val is not None:
                ax.annotate(
                    f"{val}{value_suffix}",
                    (period_labels[j], val),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8, color=CHART_TEXT_COLOUR,
                    fontweight="bold",
                )

    if title:
        ax.set_title(title, fontsize=12, color=CHART_TEXT_COLOUR,
                      fontweight="bold", pad=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=CHART_TEXT_COLOUR)

    ax.tick_params(axis="x", labelsize=9, labelcolor=CHART_TEXT_COLOUR)
    ax.tick_params(axis="y", labelsize=9, labelcolor=CHART_TEXT_COLOUR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#d1d5db")
    ax.spines["bottom"].set_color("#d1d5db")
    ax.grid(axis="y", alpha=0.3, color="#d1d5db")

    if len(series) > 1:
        ax.legend(fontsize=9, framealpha=0.9)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_metric_charts(metric_results: list[dict], section_title: str = "") -> list[dict]:
    """Generate chart images for metric results from template-driven reports.

    For each metric in metric_results, generates a bar chart showing the
    value across demographic groups.  This implements the DRR's `chart`
    ReportSection type: "Trend visualisation over last 4 periods."

    Since historical period data is not yet available in the current
    pipeline (single-period generation), bar charts comparing demographic
    groups are generated as the primary visualisation.  Line charts will
    be added when multi-period data is available.

    Args:
        metric_results: List from compute_template_metrics() — each dict
            has "label", "aggregation", and "values" (per demographic group).
        section_title: Optional section title for chart grouping.

    Returns:
        List of dicts: [{"label": "Metric Name", "chart_data_uri": "data:image/png;..."}]
    """
    if not MATPLOTLIB_AVAILABLE or not metric_results:
        return []

    charts = []
    for mr in metric_results:
        label = mr["label"]
        aggregation = mr["aggregation"]
        values_dict = mr.get("values", {})

        if not values_dict:
            continue

        # Extract labels and values from demographic groups
        group_labels = list(values_dict.keys())
        group_values = []
        for gl in group_labels:
            gd = values_dict[gl]
            val = gd.get("value", 0)
            if isinstance(val, (int, float)):
                group_values.append(float(val))
            else:
                try:
                    group_values.append(float(val))
                except (ValueError, TypeError):
                    group_values.append(0.0)

        # Determine suffix based on aggregation type
        if aggregation in ("threshold_percentage", "percentage"):
            value_suffix = "%"
            ylabel = label
        elif aggregation == "count":
            value_suffix = ""
            ylabel = f"{label} (count)"
        elif aggregation == "average":
            value_suffix = ""
            ylabel = f"{label} (mean)"
        else:
            value_suffix = ""
            ylabel = label

        chart_uri = generate_bar_chart(
            labels=group_labels,
            values=group_values,
            title=label,
            ylabel=ylabel,
            value_suffix=value_suffix,
        )

        if chart_uri:
            charts.append({
                "label": label,
                "chart_data_uri": chart_uri,
            })

    return charts
