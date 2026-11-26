from django.urls import path

from . import views

app_name = "prediction"

urlpatterns = [
    path("", views.map_page, name="map"),
    path("data/", views.map_data, name="map_data"),
    path("weather/", views.weather_overrides, name="weather_overrides"),
    path("weather/reset/<int:override_id>/", views.reset_weather_override, name="reset_weather_override"),
]
