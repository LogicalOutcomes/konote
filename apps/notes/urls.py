from django.urls import path

from . import views

app_name = "notes"
urlpatterns = [
    path("participant/<int:client_id>/", views.note_list, name="note_list"),
    path("participant/<int:client_id>/quick/", views.quick_note_create, name="quick_note_create"),
    path("participant/<int:client_id>/inline/", views.quick_note_inline, name="quick_note_inline"),
    path("participant/<int:client_id>/new/", views.note_create, name="note_create"),
    path("participant/<int:client_id>/check-date/", views.check_note_date, name="check_note_date"),
    path("<int:note_id>/", views.note_detail, name="note_detail"),
    path("<int:note_id>/summary/", views.note_summary, name="note_summary"),
    path("<int:note_id>/cancel/", views.note_cancel, name="note_cancel"),
    path("participant/<int:client_id>/qualitative/", views.qualitative_summary, name="qualitative_summary"),
]
