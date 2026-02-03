"""URL configuration for registration app."""
from django.urls import path

from . import admin_views, views

app_name = "registration"

urlpatterns = [
    # Public (no login required)
    path(
        "register/<slug:slug>/",
        views.public_registration_form,
        name="public_registration_form",
    ),
    path(
        "register/<slug:slug>/submitted/",
        views.registration_submitted,
        name="registration_submitted",
    ),

    # Admin (login required)
    path(
        "admin/registration/",
        admin_views.link_list,
        name="registration_link_list",
    ),
    path(
        "admin/registration/create/",
        admin_views.link_create,
        name="registration_link_create",
    ),
    path(
        "admin/registration/<int:pk>/edit/",
        admin_views.link_edit,
        name="registration_link_edit",
    ),
    path(
        "admin/registration/<int:pk>/delete/",
        admin_views.link_delete,
        name="registration_link_delete",
    ),

    # Submissions
    path(
        "admin/submissions/",
        admin_views.submission_list,
        name="submission_list",
    ),
    path(
        "admin/submissions/<int:pk>/",
        admin_views.submission_detail,
        name="submission_detail",
    ),
    path(
        "admin/submissions/<int:pk>/approve/",
        admin_views.submission_approve,
        name="submission_approve",
    ),
    path(
        "admin/submissions/<int:pk>/reject/",
        admin_views.submission_reject,
        name="submission_reject",
    ),
    path(
        "admin/submissions/<int:pk>/waitlist/",
        admin_views.submission_waitlist,
        name="submission_waitlist",
    ),
    path(
        "admin/submissions/<int:pk>/merge/",
        admin_views.submission_merge,
        name="submission_merge",
    ),
]
