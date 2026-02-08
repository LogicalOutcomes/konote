"""URL patterns for AI-powered HTMX endpoints."""
from django.urls import path

from konote import ai_views

app_name = "ai"
urlpatterns = [
    path("suggest-metrics/", ai_views.suggest_metrics_view, name="suggest_metrics"),
    path("improve-outcome/", ai_views.improve_outcome_view, name="improve_outcome"),
    path("generate-narrative/", ai_views.generate_narrative_view, name="generate_narrative"),
    path("suggest-note-structure/", ai_views.suggest_note_structure_view, name="suggest_note_structure"),
    path("outcome-insights/", ai_views.outcome_insights_view, name="outcome_insights"),
]
