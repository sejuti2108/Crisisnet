from django.urls import path

from . import views

app_name = "prediction"

urlpatterns = [
    path("", views.map_page, name="map"),
    path("data/", views.map_data, name="map_data"),
]