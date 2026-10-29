from django.urls import path
from . import views

urlpatterns = [
    path("", views.incident_list, name="incident_list"),
    path("<int:incident_id>/", views.incident_detail, name="incident_detail"),
    path("<int:incident_id>/update-status/", views.update_incident_status, name="update_incident_status"),
]
