"""Helpers for admin-facing taxonomy classification review workflows."""
from difflib import SequenceMatcher
import re

from django.db.models import Q
from django.utils import timezone

from apps.admin_settings.models import CidsCodeList, TaxonomyMapping
from apps.reports.pii_scrub import scrub_pii
from konote import ai


SUBJECT_TYPES = [
    ("metric", "Metric"),
    ("target", "Target"),
    ("program", "Program"),
]

IRIS_LISTS = {"IrisMetric53", "IRISImpactTheme", "IRISImpactCategory"}
SDG_LISTS = {"SDGImpacts"}


def get_taxonomy_list_choices():
    """Return available imported code lists as form choices."""
    names = list(
        CidsCodeList.objects.order_by("list_name")
        .values_list("list_name", flat=True)
        .distinct()
    )
    return [(name, name) for name in names]


def search_taxonomy_entries(list_name, query, limit=20):
    """Search imported entries so admins can manually pick a code."""
    normalized_query = str(query or "").strip()
    if not list_name or not normalized_query:
        return []

    queryset = CidsCodeList.objects.filter(list_name=list_name).filter(
        Q(code__icontains=normalized_query)
        | Q(label__icontains=normalized_query)
        | Q(label_fr__icontains=normalized_query)
        | Q(description__icontains=normalized_query)
    ).order_by("code")
    return list(queryset[:limit])


def infer_taxonomy_system(list_name):
    """Map a code-list name to the higher-level taxonomy system."""
    if list_name in SDG_LISTS:
        return "sdg"
    if list_name in IRIS_LISTS:
        return "iris_plus"
    return "common_approach"


def get_subject_queryset(subject_type):
    """Return the queryset of items that can be classified for a subject type."""
    if subject_type == "metric":
        from apps.plans.models import MetricDefinition

        return MetricDefinition.objects.filter(status="active", is_enabled=True).order_by("name")
    if subject_type == "program":
        from apps.programs.models import Program

        return Program.objects.filter(status="active").order_by("name")
    if subject_type == "target":
        from apps.plans.models import PlanTarget

        return PlanTarget.objects.select_related("client_file", "plan_section__program").filter(
            status="default",
        ).order_by("updated_at")
    raise ValueError(f"Unknown subject type: {subject_type}")


def get_subject_mapping_filter(subject_type, subject):
    """Return filter kwargs selecting mappings for the supplied subject."""
    if subject_type == "metric":
        return {"metric_definition_id": subject.pk}
    if subject_type == "program":
        return {"program_id": subject.pk}
    if subject_type == "target":
        return {"plan_target_id": subject.pk}
    raise ValueError(f"Unknown subject type: {subject_type}")


def get_subject_display(subject_type, subject):
    """Return a short label for the subject being classified."""
    if subject_type in {"metric", "program"}:
        return subject.name
    return subject.name or "Untitled target"


def get_subject_text(subject_type, subject):
    """Return scrubbed text used for heuristic and AI-assisted classification."""
    if subject_type == "metric":
        parts = [
            subject.name,
            subject.definition,
            subject.category,
            subject.unit,
        ]
        return "\n".join(part for part in parts if part)

    if subject_type == "program":
        parts = [subject.name, subject.description, subject.description_fr]
        return "\n".join(part for part in parts if part)

    if subject_type == "target":
        known_names = {
            subject.client_file.first_name,
            subject.client_file.last_name,
            subject.client_file.preferred_name,
        }
        program_name = ""
        if subject.plan_section and subject.plan_section.program:
            program_name = subject.plan_section.program.name
        parts = [
            subject.name,
            subject.description,
            subject.client_goal,
            program_name,
        ]
        return scrub_pii("\n".join(part for part in parts if part), known_names=known_names)

    raise ValueError(f"Unknown subject type: {subject_type}")


def get_related_mappings(mapping):
    """Return mappings for the same subject and code list as the supplied mapping."""
    return TaxonomyMapping.objects.filter(
        taxonomy_system=mapping.taxonomy_system,
        taxonomy_list_name=mapping.taxonomy_list_name,
        **get_subject_mapping_filter(mapping.subject_type, mapping.subject_object),
    )


def get_review_queryset(mapping_status="draft", taxonomy_system="", taxonomy_list_name="", subject_type=""):
    """Return taxonomy mappings filtered for the admin review queue."""
    qs = TaxonomyMapping.objects.select_related(
        "metric_definition", "program", "plan_target", "reviewed_by",
    ).order_by("mapping_status", "taxonomy_system", "taxonomy_list_name", "taxonomy_code")

    if mapping_status:
        qs = qs.filter(mapping_status=mapping_status)
    if taxonomy_system:
        qs = qs.filter(taxonomy_system=taxonomy_system)
    if taxonomy_list_name:
        qs = qs.filter(taxonomy_list_name=taxonomy_list_name)
    if subject_type == "metric":
        qs = qs.filter(metric_definition__isnull=False)
    elif subject_type == "program":
        qs = qs.filter(program__isnull=False)
    elif subject_type == "target":
        qs = qs.filter(plan_target__isnull=False)
    return qs


def _tokenize(text):
    return {
        token for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if len(token) > 2
    }


def _score_candidate(subject_text, entry):
    subject_tokens = _tokenize(subject_text)
    candidate_text = " ".join([
        entry.code,
        entry.label,
        entry.label_fr,
        entry.description,
    ])
    candidate_tokens = _tokenize(candidate_text)
    overlap = len(subject_tokens & candidate_tokens) / max(len(subject_tokens), 1)
    sequence = SequenceMatcher(None, subject_text.lower(), candidate_text.lower()).ratio()
    return (overlap * 0.7) + (sequence * 0.3), sorted(subject_tokens & candidate_tokens)


def _build_heuristic_suggestions(subject_type, subject, list_name, max_suggestions=3):
    subject_text = get_subject_text(subject_type, subject)
    subject_display = get_subject_display(subject_type, subject)
    entries = list(CidsCodeList.objects.filter(list_name=list_name).order_by("code"))

    scored = []
    for entry in entries:
        score, matches = _score_candidate(subject_text, entry)
        scored.append((score, matches, entry))

    scored.sort(key=lambda item: (-item[0], item[2].code))
    top = scored[:max_suggestions]
    suggestions = []
    for idx, (score, matches, entry) in enumerate(top, start=1):
        reason = (
            f"Matched keywords: {', '.join(matches[:4])}."
            if matches else
            f"Best available match in {list_name} for {subject_display}."
        )
        confidence = max(0.15, min(0.95, round(score, 2)))
        suggestions.append({
            "code": entry.code,
            "label": entry.label,
            "confidence": confidence,
            "reason": reason,
            "rank": idx,
        })
    return subject_text, suggestions


def generate_subject_suggestions(subject_type, subject, list_name, max_suggestions=3):
    """Return up to max_suggestions draft mappings for one subject."""
    subject_text, heuristic = _build_heuristic_suggestions(
        subject_type, subject, list_name, max_suggestions=max_suggestions,
    )

    candidate_entries = [
        {
            "code": item["code"],
            "label": item["label"],
            "reason": item["reason"],
        }
        for item in heuristic[: min(len(heuristic), 5)]
    ]
    ai_suggestions = None
    if ai.is_ai_available() and candidate_entries:
        ai_suggestions = ai.suggest_taxonomy_mappings(
            subject_type=subject_type,
            subject_title=get_subject_display(subject_type, subject),
            subject_text=subject_text,
            taxonomy_list_name=list_name,
            candidates=candidate_entries,
            max_suggestions=max_suggestions,
        )

    if ai_suggestions:
        ranked = []
        by_code = {item["code"]: item for item in heuristic}
        for idx, item in enumerate(ai_suggestions, start=1):
            base = by_code.get(item.get("code"), {})
            ranked.append({
                "code": item.get("code", base.get("code", "")),
                "label": item.get("label", base.get("label", "")),
                "confidence": item.get("confidence", base.get("confidence", 0.5)),
                "reason": item.get("reason", base.get("reason", "")),
                "rank": idx,
                "source": "ai_suggested",
            })
        return ranked

    return [
        {**item, "source": "system_suggested"}
        for item in heuristic
    ]


def create_draft_suggestions(subject_type, subject, list_name, user=None, max_suggestions=3):
    """Generate and persist draft suggestions for a single subject and code list."""
    taxonomy_system = infer_taxonomy_system(list_name)
    filter_kwargs = get_subject_mapping_filter(subject_type, subject)
    now = timezone.now()

    TaxonomyMapping.objects.filter(
        mapping_status="draft",
        taxonomy_system=taxonomy_system,
        taxonomy_list_name=list_name,
        **filter_kwargs,
    ).update(
        mapping_status="superseded",
        reviewed_at=now,
        reviewed_by_id=getattr(user, "pk", None),
    )

    suggestions = generate_subject_suggestions(
        subject_type, subject, list_name, max_suggestions=max_suggestions,
    )
    created = []
    for item in suggestions:
        mapping = TaxonomyMapping.objects.create(
            taxonomy_system=taxonomy_system,
            taxonomy_list_name=list_name,
            taxonomy_code=item["code"],
            taxonomy_label=item["label"],
            mapping_status="draft",
            mapping_source=item["source"],
            confidence_score=item["confidence"],
            rationale=item["reason"],
            **filter_kwargs,
        )
        created.append(mapping)
    return created


def generate_batch_suggestions(subject_type, list_name, user=None, max_items=25, max_suggestions=3, only_unmapped=True):
    """Create draft suggestions for many subjects, returning summary counts."""
    taxonomy_system = infer_taxonomy_system(list_name)
    created_count = 0
    skipped_count = 0
    created_mappings = []

    for subject in get_subject_queryset(subject_type)[:max_items]:
        filter_kwargs = get_subject_mapping_filter(subject_type, subject)
        if only_unmapped and TaxonomyMapping.objects.filter(
            taxonomy_system=taxonomy_system,
            taxonomy_list_name=list_name,
            mapping_status__in=["draft", "approved"],
            **filter_kwargs,
        ).exists():
            skipped_count += 1
            continue

        mappings = create_draft_suggestions(
            subject_type, subject, list_name, user=user, max_suggestions=max_suggestions,
        )
        created_count += len(mappings)
        created_mappings.extend(mappings)

    return {
        "created_count": created_count,
        "skipped_count": skipped_count,
        "created_mappings": created_mappings,
    }


def answer_taxonomy_question(mapping, question, history=None):
    """Answer an admin question about a mapping suggestion.

    Falls back to a deterministic explanation if AI is unavailable.
    """
    subject = mapping.subject_object
    subject_type = mapping.subject_type
    subject_text = get_subject_text(subject_type, subject)
    alternatives = [
        {
            "code": item.taxonomy_code,
            "label": item.taxonomy_label,
            "reason": item.rationale,
            "status": item.mapping_status,
        }
        for item in get_related_mappings(mapping)
            .exclude(pk=mapping.pk)
            .order_by("mapping_status", "taxonomy_code")[:5]
    ]

    if ai.is_ai_available():
        answer = ai.answer_taxonomy_review_question(
            subject_type=subject_type,
            subject_title=get_subject_display(subject_type, subject),
            subject_text=subject_text,
            taxonomy_system=mapping.taxonomy_system,
            taxonomy_list_name=mapping.taxonomy_list_name,
            current_mapping={
                "code": mapping.taxonomy_code,
                "label": mapping.taxonomy_label,
                "reason": mapping.rationale,
                "confidence": mapping.confidence_score,
            },
            alternatives=alternatives,
            question=question,
            history=history or [],
        )
        if answer:
            return answer

    answer_lines = [
        f"Current suggestion: {mapping.taxonomy_code} — {mapping.taxonomy_label}.",
    ]
    if mapping.rationale:
        answer_lines.append(f"Reason: {mapping.rationale}")
    if alternatives:
        formatted = "; ".join(
            f"{item['code']} — {item['label']}" for item in alternatives
        )
        answer_lines.append(f"Other suggestions available: {formatted}.")
    answer_lines.append(
        "To change the reporting lens, rerun suggestions for this item with a different code list."
    )
    return " ".join(answer_lines)
