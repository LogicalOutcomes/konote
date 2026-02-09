"""URL configuration for the participant portal.

All portal URLs are mounted under /my/ in the root urlconf.
Pre-auth routes (login, safety, invite, password reset) do not require
a portal session. Everything else uses @portal_login_required.
"""
from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    # Auth (some pre-auth)
    path("login/", views.portal_login, name="login"),
    path("logout/", views.portal_logout, name="logout"),
    path("emergency-logout/", views.emergency_logout, name="emergency_logout"),
    path("invite/<str:token>/", views.accept_invite, name="accept_invite"),
    path("consent/", views.consent_flow, name="consent_flow"),
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
    path("safety/", views.safety_help, name="safety_help"),
    # Password
    path("password/change/", views.password_change, name="change_password"),
    path("password/reset/", views.password_reset_request, name="forgot_password"),
    path("password/reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    path("settings/", views.settings_view, name="settings"),
    # Goals (Phase B)
    path("goals/", views.goals_list, name="goals"),
    path("goals/<int:target_id>/", views.goal_detail, name="goal_detail"),
    path("progress/", views.progress_view, name="progress"),
    path("my-words/", views.my_words, name="my_words"),
    path("milestones/", views.milestones, name="milestones"),
    path("correction/new/", views.correction_request_create, name="correction_request"),
    # Journal + Messages (Phase C)
    path("journal/", views.journal_list, name="journal"),
    path("journal/new/", views.journal_create, name="journal_new"),
    path("journal/disclosure/", views.journal_disclosure, name="journal_disclosure"),
    path("message/", views.message_create, name="message_to_worker"),
    path("discuss-next/", views.discuss_next, name="discuss_next"),
]
