"""Helpers for portal survey rendering: page grouping, conditional sections."""


def group_sections_into_pages(sections):
    """Group a list of SurveySection objects into pages.

    Sections are grouped sequentially. A section with page_break=True
    starts a new page. Returns a list of lists.
    """
    if not sections:
        return []
    pages = [[]]
    for section in sections:
        if section.page_break and pages[-1]:
            pages.append([])
        pages[-1].append(section)
    return pages


def filter_visible_sections(sections, partial_answers):
    """Filter sections based on conditional visibility.

    Args:
        sections: list of SurveySection objects (ordered by sort_order)
        partial_answers: dict of {question_pk: value_string} from PartialAnswer

    Returns:
        list of visible SurveySection objects
    """
    visible = []
    for section in sections:
        if section.condition_question_id is None:
            visible.append(section)
        else:
            answer = partial_answers.get(section.condition_question_id, "")
            if answer == section.condition_value:
                visible.append(section)
    return visible


def get_partial_answers_dict(assignment):
    """Load all PartialAnswer values for an assignment as {question_pk: value}."""
    from apps.surveys.models import PartialAnswer
    partials = PartialAnswer.objects.filter(assignment=assignment)
    return {pa.question_id: pa.value for pa in partials}


def calculate_section_scores(sections, answers_dict):
    """Calculate scores for scored sections.

    Args:
        sections: list of SurveySection objects
        answers_dict: dict of {question_pk: value_string}

    Returns:
        list of dicts: [{"title": str, "score": int, "max_score": int}, ...]
        Only includes sections with scoring_method != "none".
    """
    scores = []
    for section in sections:
        if section.scoring_method == "none" or not section.max_score:
            continue
        total = 0
        for question in section.questions.all().order_by("sort_order"):
            answer_val = answers_dict.get(question.pk, "")
            if not answer_val:
                continue
            if question.question_type in ("rating_scale", "yes_no"):
                try:
                    total += int(answer_val)
                except (ValueError, TypeError):
                    pass
            elif question.question_type == "single_choice":
                for opt in (question.options_json or []):
                    if opt.get("value") == answer_val and opt.get("score") is not None:
                        total += opt["score"]
                        break
        scores.append({
            "title": section.title,
            "score": total,
            "max_score": section.max_score,
        })
    return scores
