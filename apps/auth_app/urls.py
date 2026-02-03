from django.urls import path
from . import admin_views, views

app_name = "auth_app"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("callback/", views.azure_callback, name="azure_callback"),
    path("logout/", views.logout_view, name="logout"),
    # User management (admin only)
    path("users/", admin_views.user_list, name="user_list"),
    path("users/new/", admin_views.user_create, name="user_create"),
    path("users/<int:user_id>/edit/", admin_views.user_edit, name="user_edit"),
    path("users/<int:user_id>/deactivate/", admin_views.user_deactivate, name="user_deactivate"),
]
