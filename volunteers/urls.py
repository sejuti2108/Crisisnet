from django.urls import path
from . import views

urlpatterns = [
    path("manage/", views.volunteer_management, name="volunteer_management"),
    path("<int:volunteer_id>/assign/", views.assign_volunteer, name="assign_volunteer"),
    path("dashboard/", views.volunteer_dashboard, name="volunteer_dashboard"),
]
