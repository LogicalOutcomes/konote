"""URL patterns for client data erasure workflow."""
from django.urls import path

from . import erasure_views

urlpatterns = [
    path("", erasure_views.erasure_pending_list, name="erasure_pending_list"),
    path("history/", erasure_views.erasure_history, name="erasure_history"),
    path("<int:pk>/", erasure_views.erasure_request_detail, name="erasure_request_detail"),
    path("<int:pk>/approve/", erasure_views.erasure_approve, name="erasure_approve"),
    path("<int:pk>/reject/", erasure_views.erasure_reject, name="erasure_reject"),
    path("<int:pk>/cancel/", erasure_views.erasure_cancel, name="erasure_cancel"),
    path("<int:pk>/cancel-scheduled/", erasure_views.erasure_cancel_scheduled, name="erasure_cancel_scheduled"),
    path("<int:pk>/receipt/", erasure_views.erasure_receipt_pdf, name="erasure_receipt_pdf"),
]
