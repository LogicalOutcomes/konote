from django.urls import path

from . import views

app_name = "field_collection"
urlpatterns = [
    path("", views.field_collection_list, name="list"),
    path("<int:program_id>/", views.field_collection_edit, name="edit"),
]
