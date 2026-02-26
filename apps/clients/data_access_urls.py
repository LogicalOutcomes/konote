from django.urls import path

from .data_access_views import data_access_checklist, data_access_complete, data_access_log

app_name = "data_access"

urlpatterns = [
    path("<int:pk>/", data_access_checklist, name="data_access_checklist"),
    path("<int:pk>/complete/", data_access_complete, name="data_access_complete"),
]
