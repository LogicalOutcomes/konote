from django.urls import path

from . import admin_views

# These are included under /admin/settings/users/ in KoNote/urls.py
# but use auth_app namespace via the main urls.py app_name
urlpatterns = [
    path("", admin_views.user_list, name="user_list"),
    path("new/", admin_views.user_create, name="user_create"),
    path("<int:user_id>/edit/", admin_views.user_edit, name="user_edit"),
    path("<int:user_id>/deactivate/", admin_views.user_deactivate, name="user_deactivate"),
    path("<int:user_id>/impersonate/", admin_views.impersonate_user, name="impersonate_user"),
]
