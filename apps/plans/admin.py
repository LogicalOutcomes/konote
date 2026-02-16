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
    list_display = ("name", "name_fr", "category", "is_library", "is_enabled", "status")
    list_filter = ("category", "is_library", "is_enabled", "status")
    search_fields = ("name", "name_fr")


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
