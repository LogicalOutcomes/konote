from django.urls import path
from . import access_grant_views, invite_views, views

app_name = "auth_app"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("callback/", views.azure_callback, name="azure_callback"),
    path("logout/", views.logout_view, name="logout"),
    # Demo login (only works when DEMO_MODE is enabled)
    path("demo-login/<str:role>/", views.demo_login, name="demo_login"),
    path("demo-portal-login/", views.demo_portal_login, name="demo_portal_login"),
    # MFA (TOTP)
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/disable/", views.mfa_disable, name="mfa_disable"),
    # Invite accept (public — user clicks link from email)
    path("join/<uuid:code>/", invite_views.invite_accept, name="invite_accept"),
    # Access grants (GATED clinical access — Tier 3)
    path("access-grant/request/", access_grant_views.access_grant_request, name="access_grant_request"),
    path("access-grants/", access_grant_views.access_grant_list, name="access_grant_list"),
    path("access-grants/<int:grant_id>/revoke/", access_grant_views.access_grant_revoke, name="access_grant_revoke"),
]
