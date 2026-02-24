from django.contrib import admin

from .models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
    PlanTemplate,
    PlanTemplateSection,
    PlanTemplateTarget,
)


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "category", "metric_type", "is_library", "is_enabled", "status")
    list_filter = ("category", "metric_type", "is_library", "is_enabled", "status")
    search_fields = ("name", "name_fr")
    fieldsets = (
        (None, {
            "fields": ("name", "name_fr", "definition", "definition_fr", "category", "metric_type"),
        }),
        ("Scale metric settings", {
            "classes": ("collapse",),
            "description": "Only applies when metric type is 'Numeric scale'.",
            "fields": ("min_value", "max_value", "unit", "unit_fr", "higher_is_better",
                        "threshold_low", "threshold_high", "target_band_high_pct"),
        }),
        ("Achievement metric settings", {
            "classes": ("collapse",),
            "description": "Only applies when metric type is 'Achievement'.",
            "fields": ("achievement_options", "achievement_success_values", "target_rate"),
        }),
        ("Visibility & ownership", {
            "fields": ("is_library", "is_universal", "is_enabled", "status",
                        "owning_program", "computation_type"),
        }),
        ("Participant portal", {
            "classes": ("collapse",),
            "fields": ("portal_description", "portal_description_fr", "portal_visibility"),
        }),
    )


@admin.register(PlanSection)
class PlanSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "client_file", "program", "sort_order")


@admin.register(PlanTarget)
class PlanTargetAdmin(admin.ModelAdmin):
    list_display = ("name", "plan_section", "status", "sort_order")
    list_filter = ("status",)


@admin.register(PlanTargetRevision)
class PlanTargetRevisionAdmin(admin.ModelAdmin):
    list_display = ("plan_target", "changed_by", "created_at")


@admin.register(PlanTargetMetric)
class PlanTargetMetricAdmin(admin.ModelAdmin):
    list_display = ("plan_target", "metric_def", "sort_order")


@admin.register(PlanTemplate)
class PlanTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "status", "created_at")
    list_filter = ("status",)


@admin.register(PlanTemplateSection)
class PlanTemplateSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "plan_template", "sort_order")


@admin.register(PlanTemplateTarget)
class PlanTemplateTargetAdmin(admin.ModelAdmin):
    list_display = ("name", "template_section", "sort_order")
