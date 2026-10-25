from django.contrib import admin
from django.urls import path

from requests_app.views import live_test
from requests_app.dashboard import (
    dashboard,
    approve_action,
    reject_action,
    dispatch_action,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("live/", live_test),
    path("coordinator/", dashboard, name="dashboard"),
    path("coordinator/approve/<int:request_id>/", approve_action, name="approve"),
    path("coordinator/reject/<int:request_id>/", reject_action, name="reject"),
    path("coordinator/dispatch/<int:request_id>/", dispatch_action, name="dispatch"),
]