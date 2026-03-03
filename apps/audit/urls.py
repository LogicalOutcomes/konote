from django.urls import path
from . import views

app_name = "audit"
urlpatterns = [
    path("", views.audit_log_list, name="audit_log_list"),
    path("export/", views.audit_log_export, name="audit_log_export"),
    path("compliance/", views.compliance_summary, name="compliance_summary"),
]
