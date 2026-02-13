from django.urls import path

from . import admin_views, invite_views

app_name = "admin_users"

urlpatterns = [
    path("", admin_views.user_list, name="user_list"),
    path("new/", admin_views.user_create, name="user_create"),
    path("<int:user_id>/edit/", admin_views.user_edit, name="user_edit"),
    path("<int:user_id>/deactivate/", admin_views.user_deactivate, name="user_deactivate"),
    path("<int:user_id>/impersonate/", admin_views.impersonate_user, name="impersonate_user"),
    path("<int:user_id>/roles/", admin_views.user_roles, name="user_roles"),
    path("<int:user_id>/roles/add/", admin_views.user_role_add, name="user_role_add"),
    path("<int:user_id>/roles/<int:role_id>/remove/", admin_views.user_role_remove, name="user_role_remove"),
    # Invites
    path("invites/", invite_views.invite_list, name="invite_list"),
    path("invites/new/", invite_views.invite_create, name="invite_create"),
]
