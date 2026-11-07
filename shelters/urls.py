from django.urls import path
from . import views

urlpatterns = [
    path("update-occupancy/<int:shelter_id>/", views.update_shelter_occupancy, name="update_shelter_occupancy"),
    path("request-supplies/<int:shelter_id>/", views.create_supply_request, name="create_supply_request"),
]
