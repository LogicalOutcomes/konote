from django.contrib import admin

from .models import (
    MetricValue,
    ProgressNote,
    ProgressNoteTarget,
    ProgressNoteTemplate,
    ProgressNoteTemplateMetric,
    ProgressNoteTemplateSection,
)


@admin.register(ProgressNoteTemplate)
class ProgressNoteTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "status", "created_at")
    list_filter = ("status",)


@admin.register(ProgressNoteTemplateSection)
class ProgressNoteTemplateSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "section_type", "sort_order")


@admin.register(ProgressNoteTemplateMetric)
class ProgressNoteTemplateMetricAdmin(admin.ModelAdmin):
    list_display = ("template_section", "metric_def", "sort_order")


@admin.register(ProgressNote)
class ProgressNoteAdmin(admin.ModelAdmin):
    list_display = ("client_file", "author", "note_type", "created_at")
    list_filter = ("note_type", "status")


@admin.register(ProgressNoteTarget)
class ProgressNoteTargetAdmin(admin.ModelAdmin):
    list_display = ("progress_note", "plan_target", "created_at")


@admin.register(MetricValue)
class MetricValueAdmin(admin.ModelAdmin):
    list_display = ("progress_note_target", "metric_def", "value")
