from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
    path("dashboard/admin/", views.dashboard_admin, name="dashboard_admin"),
    path("dashboard/coordinator/", views.dashboard_coordinator, name="dashboard_coordinator"),
    path("dashboard/shelter-manager/", views.dashboard_shelter_manager, name="dashboard_shelter_manager"),
    path("dashboard/volunteer/", views.dashboard_volunteer, name="dashboard_volunteer"),
    path("dashboard/admin/create-account/", views.admin_create_account, name="admin_create_account"),
]
