"""URL patterns for suggestion theme management."""
from django.urls import path

from . import suggestion_views

app_name = "suggestion_themes"

urlpatterns = [
    path("", suggestion_views.theme_list, name="theme_list"),
    path("create/", suggestion_views.theme_form, name="theme_create"),
    path("<int:pk>/", suggestion_views.theme_detail, name="theme_detail"),
    path("<int:pk>/edit/", suggestion_views.theme_form, name="theme_edit"),
    path("<int:pk>/unlinked/", suggestion_views.unlinked_partial, name="unlinked_partial"),
]
