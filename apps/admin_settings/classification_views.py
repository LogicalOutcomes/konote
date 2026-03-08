"""Admin views for taxonomy classification review and approval."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.auth_app.decorators import admin_required, demo_read_only
from apps.admin_settings.classification_forms import (
    TaxonomyBatchSuggestForm,
    TaxonomyBulkActionForm,
    TaxonomyManualPickForm,
    TaxonomyManualSearchForm,
    TaxonomyQueueFilterForm,
    TaxonomyQuestionForm,
    TaxonomyReclassifyForm,
)
from apps.admin_settings.models import CidsCodeList, TaxonomyMapping
from apps.admin_settings.taxonomy_review import (
    answer_taxonomy_question,
    create_draft_suggestions,
    generate_batch_suggestions,
    get_related_mappings,
    get_review_queryset,
    search_taxonomy_entries,
)


def _conversation_key(mapping_id):
    return f"taxonomy_review_conversation_{mapping_id}"


def _approve_mapping(mapping, user):
    now = timezone.now()
    related = get_related_mappings(mapping).exclude(pk=mapping.pk).filter(
        mapping_status__in=["draft", "approved"],
    )
    related.update(mapping_status="superseded", reviewed_by_id=user.pk, reviewed_at=now)

    mapping.mapping_status = "approved"
    mapping.reviewed_by = user
    mapping.reviewed_at = now
    mapping.save(update_fields=["mapping_status", "reviewed_by", "reviewed_at"])


def _reject_mapping(mapping, user):
    mapping.mapping_status = "rejected"
    mapping.reviewed_by = user
    mapping.reviewed_at = timezone.now()
    mapping.save(update_fields=["mapping_status", "reviewed_by", "reviewed_at"])


@login_required
@admin_required
def taxonomy_review_queue(request):
    filter_form = TaxonomyQueueFilterForm(request.GET or None)
    filters = {
        "mapping_status": "draft",
        "taxonomy_system": "",
        "taxonomy_list_name": "",
        "subject_type": "",
    }
    if filter_form.is_valid():
        filters.update({key: filter_form.cleaned_data.get(key) or "" for key in filters})
    mappings = get_review_queryset(**filters)

    generate_form = TaxonomyBatchSuggestForm()
    bulk_form = TaxonomyBulkActionForm()
    return render(request, "admin_settings/classification/queue.html", {
        "filter_form": filter_form,
        "generate_form": generate_form,
        "bulk_form": bulk_form,
        "mappings": mappings,
    })


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_generate_suggestions(request):
    form = TaxonomyBatchSuggestForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please correct the batch suggestion form.")
        return redirect("admin_settings:taxonomy_review_queue")

    result = generate_batch_suggestions(
        subject_type=form.cleaned_data["subject_type"],
        list_name=form.cleaned_data["taxonomy_list_name"],
        user=request.user,
        max_items=form.cleaned_data["max_items"],
        max_suggestions=form.cleaned_data["max_suggestions"],
        only_unmapped=form.cleaned_data["only_unmapped"],
    )
    messages.success(
        request,
        f"Created {result['created_count']} draft mapping suggestion(s); skipped {result['skipped_count']} existing item(s).",
    )
    return redirect(
        f"/admin/settings/classification/?mapping_status=draft&taxonomy_list_name={form.cleaned_data['taxonomy_list_name']}"
    )


@login_required
@admin_required
def taxonomy_mapping_detail(request, mapping_id):
    mapping = get_object_or_404(
        TaxonomyMapping.objects.select_related(
            "metric_definition", "program", "plan_target", "reviewed_by",
        ),
        pk=mapping_id,
    )
    related_mappings = get_related_mappings(mapping).exclude(pk=mapping.pk)
    conversation = request.session.get(_conversation_key(mapping.pk), [])
    question_form = TaxonomyQuestionForm()
    manual_search_form = TaxonomyManualSearchForm(request.GET or None)
    manual_search_results = []
    if manual_search_form.is_valid() and manual_search_form.cleaned_data.get("query"):
        manual_search_results = search_taxonomy_entries(
            mapping.taxonomy_list_name,
            manual_search_form.cleaned_data["query"],
        )
    reclassify_form = TaxonomyReclassifyForm(initial={
        "taxonomy_list_name": mapping.taxonomy_list_name,
        "max_suggestions": 3,
    })
    return render(request, "admin_settings/classification/detail.html", {
        "mapping": mapping,
        "related_mappings": related_mappings,
        "conversation": conversation,
        "question_form": question_form,
        "manual_search_form": manual_search_form,
        "manual_search_results": manual_search_results,
        "reclassify_form": reclassify_form,
    })


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_mapping_approve(request, mapping_id):
    mapping = get_object_or_404(TaxonomyMapping, pk=mapping_id)
    _approve_mapping(mapping, request.user)
    messages.success(request, "Mapping approved.")
    return redirect("admin_settings:taxonomy_review_queue")


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_mapping_reject(request, mapping_id):
    mapping = get_object_or_404(TaxonomyMapping, pk=mapping_id)
    _reject_mapping(mapping, request.user)
    messages.success(request, "Mapping rejected.")
    return redirect("admin_settings:taxonomy_review_queue")


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_bulk_action(request):
    form = TaxonomyBulkActionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Select at least one draft mapping and action.")
        return redirect("admin_settings:taxonomy_review_queue")

    mappings = list(
        TaxonomyMapping.objects.filter(
            pk__in=form.cleaned_data["mapping_ids"],
            mapping_status="draft",
        )
    )
    if not mappings:
        messages.error(request, "No draft mappings were selected.")
        return redirect("admin_settings:taxonomy_review_queue")

    action = form.cleaned_data["action"]
    for mapping in mappings:
        if action == "approve":
            _approve_mapping(mapping, request.user)
        else:
            _reject_mapping(mapping, request.user)

    action_label = "approved" if action == "approve" else "rejected"
    messages.success(request, f"{len(mappings)} mapping(s) {action_label}.")
    return redirect("admin_settings:taxonomy_review_queue")


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_mapping_reclassify(request, mapping_id):
    mapping = get_object_or_404(TaxonomyMapping, pk=mapping_id)
    form = TaxonomyReclassifyForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a code list before rerunning classification.")
        return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=mapping.pk)

    created = create_draft_suggestions(
        mapping.subject_type,
        mapping.subject_object,
        form.cleaned_data["taxonomy_list_name"],
        user=request.user,
        max_suggestions=form.cleaned_data["max_suggestions"],
    )
    messages.success(request, f"Created {len(created)} new draft suggestion(s).")
    if created:
        return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=created[0].pk)
    return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=mapping.pk)


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_mapping_manual_pick(request, mapping_id):
    mapping = get_object_or_404(TaxonomyMapping, pk=mapping_id)
    form = TaxonomyManualPickForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a code from the search results.")
        return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=mapping.pk)

    entry = get_object_or_404(
        CidsCodeList,
        list_name=mapping.taxonomy_list_name,
        code=form.cleaned_data["code"],
    )
    manual_mapping = TaxonomyMapping.objects.filter(
        taxonomy_system=mapping.taxonomy_system,
        taxonomy_list_name=mapping.taxonomy_list_name,
        taxonomy_code=entry.code,
        metric_definition_id=mapping.metric_definition_id,
        program_id=mapping.program_id,
        plan_target_id=mapping.plan_target_id,
    ).first()

    if manual_mapping is None:
        manual_mapping = TaxonomyMapping.objects.create(
            taxonomy_system=mapping.taxonomy_system,
            taxonomy_list_name=mapping.taxonomy_list_name,
            taxonomy_code=entry.code,
            taxonomy_label=entry.label,
            mapping_status="draft",
            mapping_source="manual",
            rationale="Manually selected during classification review.",
            metric_definition_id=mapping.metric_definition_id,
            program_id=mapping.program_id,
            plan_target_id=mapping.plan_target_id,
        )
    else:
        manual_mapping.taxonomy_label = entry.label
        manual_mapping.mapping_source = "manual"
        manual_mapping.rationale = "Manually selected during classification review."
        manual_mapping.save(update_fields=["taxonomy_label", "mapping_source", "rationale"])

    _approve_mapping(manual_mapping, request.user)
    messages.success(request, "Manual code selection saved and approved.")
    return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=manual_mapping.pk)


@login_required
@admin_required
@demo_read_only
@require_POST
def taxonomy_mapping_ask(request, mapping_id):
    mapping = get_object_or_404(TaxonomyMapping, pk=mapping_id)
    form = TaxonomyQuestionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a question for the review assistant.")
        return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=mapping.pk)

    session_key = _conversation_key(mapping.pk)
    conversation = request.session.get(session_key, [])
    question = form.cleaned_data["question"]
    answer = answer_taxonomy_question(mapping, question, history=conversation)
    conversation.append({"role": "user", "content": question})
    conversation.append({"role": "assistant", "content": answer})
    request.session[session_key] = conversation[-12:]
    request.session.modified = True
    return redirect("admin_settings:taxonomy_mapping_detail", mapping_id=mapping.pk)
