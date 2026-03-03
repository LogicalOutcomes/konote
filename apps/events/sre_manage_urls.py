"""URL configuration for SRE category management (mounted at /manage/sre-categories/)."""
from django.urls import path

from .views import sre_category_create, sre_category_edit, sre_category_list, sre_category_toggle_active

app_name = "sre_categories"
urlpatterns = [
    path("", sre_category_list, name="sre_category_list"),
    path("create/", sre_category_create, name="sre_category_create"),
    path("<int:category_id>/edit/", sre_category_edit, name="sre_category_edit"),
    path("<int:category_id>/toggle-active/", sre_category_toggle_active, name="sre_category_toggle_active"),
]
