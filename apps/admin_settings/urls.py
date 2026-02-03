from django.urls import path

from . import views

app_name = "admin_settings"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("terminology/", views.terminology, name="terminology"),
    path("terminology/reset/<str:term_key>/", views.terminology_reset, name="terminology_reset"),
    path("features/", views.features, name="features"),
    path("instance/", views.instance_settings, name="instance_settings"),
]
