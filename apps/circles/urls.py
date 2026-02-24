from django.urls import path

from . import views

app_name = "circles"

urlpatterns = [
    path("", views.circle_list, name="circle_list"),
    path("create/", views.circle_create, name="circle_create"),
    path("<int:circle_id>/", views.circle_detail, name="circle_detail"),
    path("<int:circle_id>/edit/", views.circle_edit, name="circle_edit"),
    path("<int:circle_id>/archive/", views.circle_archive, name="circle_archive"),
    path("<int:circle_id>/member/add/", views.membership_add, name="membership_add"),
    path(
        "<int:circle_id>/member/<int:membership_id>/remove/",
        views.membership_remove,
        name="membership_remove",
    ),
]
