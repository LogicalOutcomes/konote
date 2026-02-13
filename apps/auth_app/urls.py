from django.urls import path
from . import invite_views, views

app_name = "auth_app"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("callback/", views.azure_callback, name="azure_callback"),
    path("logout/", views.logout_view, name="logout"),
    # Demo login (only works when DEMO_MODE is enabled)
    path("demo-login/<str:role>/", views.demo_login, name="demo_login"),
    path("demo-portal-login/", views.demo_portal_login, name="demo_portal_login"),
    # Invite accept (public — user clicks link from email)
    path("join/<uuid:code>/", invite_views.invite_accept, name="invite_accept"),
]
