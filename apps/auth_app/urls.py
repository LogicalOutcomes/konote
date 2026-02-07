from django.urls import path
from . import admin_views, invite_views, views

app_name = "auth_app"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("callback/", views.azure_callback, name="azure_callback"),
    path("logout/", views.logout_view, name="logout"),
    # Demo login (only works when DEMO_MODE is enabled)
    path("demo-login/<str:role>/", views.demo_login, name="demo_login"),
    # User management (admin only)
    path("users/", admin_views.user_list, name="user_list"),
    path("users/new/", admin_views.user_create, name="user_create"),
    path("users/<int:user_id>/edit/", admin_views.user_edit, name="user_edit"),
    path("users/<int:user_id>/deactivate/", admin_views.user_deactivate, name="user_deactivate"),
    path("users/<int:user_id>/impersonate/", admin_views.impersonate_user, name="impersonate_user"),
    path("users/<int:user_id>/roles/", admin_views.user_roles, name="user_roles"),
    path("users/<int:user_id>/roles/add/", admin_views.user_role_add, name="user_role_add"),
    path("users/<int:user_id>/roles/<int:role_id>/remove/", admin_views.user_role_remove, name="user_role_remove"),
    # Invites (admin only, except accept which is public)
    path("invites/", invite_views.invite_list, name="invite_list"),
    path("invites/new/", invite_views.invite_create, name="invite_create"),
    path("join/<uuid:code>/", invite_views.invite_accept, name="invite_accept"),
]
