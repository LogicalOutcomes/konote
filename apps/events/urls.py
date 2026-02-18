from django.urls import path

from .views import (
    alert_cancel,
    alert_create,
    alert_recommend_cancel,
    alert_recommendation_queue,
    alert_recommendation_review,
    calendar_feed_settings,
    event_create,
    event_list,
    meeting_create,
    meeting_list,
    meeting_status_update,
    meeting_update,
)

app_name = "events"
urlpatterns = [
    # Client events
    path("client/<int:client_id>/", event_list, name="event_list"),
    path("client/<int:client_id>/create/", event_create, name="event_create"),
    # Alerts
    path("client/<int:client_id>/alerts/create/", alert_create, name="alert_create"),
    path("alerts/<int:alert_id>/cancel/", alert_cancel, name="alert_cancel"),
    # Alert cancellation recommendation workflow (two-person safety rule)
    path("alerts/<int:alert_id>/recommend-cancel/", alert_recommend_cancel, name="alert_recommend_cancel"),
    path("alerts/recommendations/", alert_recommendation_queue, name="alert_recommendation_queue"),
    path("alerts/recommendations/<int:recommendation_id>/review/", alert_recommendation_review, name="alert_recommendation_review"),
    # Meetings
    path("meetings/", meeting_list, name="meeting_list"),
    path("client/<int:client_id>/meetings/create/", meeting_create, name="meeting_create"),
    path("client/<int:client_id>/meetings/<int:event_id>/", meeting_update, name="meeting_update"),
    path("meetings/<int:event_id>/status/", meeting_status_update, name="meeting_status_update"),
    # Calendar feed
    path("calendar/settings/", calendar_feed_settings, name="calendar_feed_settings"),
]
