"""URL patterns for the duplicate client merge workflow."""
from django.urls import path

from . import merge_views

urlpatterns = [
    path("", merge_views.merge_candidates_list, name="merge_candidates_list"),
    path(
        "<int:client_a_id>/<int:client_b_id>/",
        merge_views.merge_compare,
        name="merge_compare",
    ),
]
