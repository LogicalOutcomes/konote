"""Survey admin configuration."""
from django.contrib import admin

from .models import (
    Survey,
    SurveyAnswer,
    SurveyAssignment,
    SurveyQuestion,
    SurveyResponse,
    SurveySection,
    SurveyTriggerRule,
)


class SurveySectionInline(admin.TabularInline):
    model = SurveySection
    extra = 0
    fields = ("title", "sort_order", "scoring_method", "is_active")


class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 0
    fields = ("question_text", "question_type", "sort_order", "required")


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [SurveySectionInline]


@admin.register(SurveySection)
class SurveySectionAdmin(admin.ModelAdmin):
    list_display = ("title", "survey", "sort_order", "is_active")
    list_filter = ("survey",)
    inlines = [SurveyQuestionInline]


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "section", "question_type", "sort_order", "required")
    list_filter = ("question_type", "required")


@admin.register(SurveyTriggerRule)
class SurveyTriggerRuleAdmin(admin.ModelAdmin):
    list_display = ("survey", "trigger_type", "is_active", "repeat_policy")
    list_filter = ("trigger_type", "is_active")


@admin.register(SurveyAssignment)
class SurveyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("survey", "participant_user", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("participant_user", "client_file")


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("survey", "channel", "submitted_at")
    list_filter = ("channel",)
    raw_id_fields = ("client_file",)


@admin.register(SurveyAnswer)
class SurveyAnswerAdmin(admin.ModelAdmin):
    list_display = ("response", "question", "numeric_value")
    raw_id_fields = ("response", "question")
