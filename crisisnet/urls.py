from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

from requests_app.views import live_test, test_broadcast
from requests_app.dashboard import (
    dashboard,
    approve_action,
    reject_action,
    dispatch_action,
)

urlpatterns = [
    path("", lambda request: redirect("dashboard_redirect"), name="home"),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("shelters/", include("shelters.urls")),
    path("incidents/", include("incidents.urls")),
    path("live/", live_test),
    path("test-broadcast/", test_broadcast),
    path("coordinator/", dashboard, name="dashboard"),
    path("coordinator/approve/<int:request_id>/", approve_action, name="approve"),
    path("coordinator/reject/<int:request_id>/", reject_action, name="reject"),
    path("coordinator/dispatch/<int:request_id>/", dispatch_action, name="dispatch"),
]