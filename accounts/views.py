from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .decorators import role_required
from .models import User


def get_dashboard_url_name(user):
    """Helper to determine the target dashboard URL name based on user role."""
    if user.is_superuser or user.role == User.Role.ADMIN:
        return "dashboard_admin"
    elif user.role == User.Role.COORDINATOR:
        return "dashboard_coordinator"
    elif user.role == User.Role.SHELTER_MANAGER:
        return "dashboard_shelter_manager"
    elif user.role == User.Role.VOLUNTEER:
        return "dashboard_volunteer"
    return "login"


def login_view(request):
    """Secure user login view with role-based redirection."""
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_name(request.user))

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")

            # Safe redirect check for 'next' query param
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            return redirect(get_dashboard_url_name(user))
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm(request)

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Secure logout view supporting both POST and GET."""
    if request.user.is_authenticated:
        auth_logout(request)
        messages.success(request, "You have been logged out successfully.")
    return redirect("login")


@login_required
def dashboard_redirect(request):
    """Central redirection endpoint that routes users to their role-specific dashboard."""
    return redirect(get_dashboard_url_name(request.user))


@role_required(User.Role.ADMIN)
def dashboard_admin(request):
    """
    Admin dashboard: Comprehensive real-time command overview aggregating:
    - Users & Roles summary
    - Shelters, total capacity, occupancy, and availability
    - Incidents, active emergencies, and severity levels
    - Volunteers, availability, and assignments
    - Warehouses & regional inventory summary
    - Relief requests and pipeline status
    """
    from django.db.models import Sum, Count
    from shelters.models import Shelter
    from incidents.models import Incident
    from volunteers.models import Volunteer
    from warehouses.models import Warehouse, InventoryItem
    from requests_app.models import Request

    # 1. Users & Roles
    users_total = User.objects.count()
    users_by_role = {
        role: User.objects.filter(role=role).count()
        for role, _ in User.Role.choices
    }
    recent_users = User.objects.order_by("-date_joined")[:5]

    # 2. Shelters
    shelters_total = Shelter.objects.count()
    shelter_capacity_total = Shelter.objects.aggregate(total=Sum("capacity"))["total"] or 0
    shelter_occupancy_total = Shelter.objects.aggregate(total=Sum("current_occupancy"))["total"] or 0
    shelters_open = Shelter.objects.filter(status=Shelter.Status.OPEN).count()
    shelters_full = Shelter.objects.filter(status=Shelter.Status.FULL).count()
    shelters_closed = Shelter.objects.filter(status=Shelter.Status.CLOSED).count()
    recent_shelters = Shelter.objects.select_related("manager").order_by("-created_at")[:5]

    # 3. Incidents
    incidents_total = Incident.objects.count()
    incidents_active = Incident.objects.filter(
        status__in=[Incident.Status.REPORTED, Incident.Status.ACTIVE]
    ).count()
    incidents_critical = Incident.objects.filter(severity=Incident.Severity.CRITICAL).count()
    recent_incidents = Incident.objects.order_by("-created_at")[:5]

    # 4. Volunteers
    volunteers_total = Volunteer.objects.count()
    volunteers_available = Volunteer.objects.filter(availability=Volunteer.Availability.AVAILABLE).count()
    volunteers_deployed = Volunteer.objects.filter(availability=Volunteer.Availability.DEPLOYED).count()
    volunteers_unavailable = Volunteer.objects.filter(availability=Volunteer.Availability.UNAVAILABLE).count()
    recent_volunteers = Volunteer.objects.select_related("user", "assigned_incident", "assigned_shelter").order_by("-created_at")[:5]

    # 5. Warehouses & Inventory
    warehouses_total = Warehouse.objects.count()
    inventory_items_total = InventoryItem.objects.count()
    total_stock_units = InventoryItem.objects.aggregate(total=Sum("quantity"))["total"] or 0
    warehouses_list = Warehouse.objects.prefetch_related("items").all()[:6]

    # 6. Requests
    requests_total = Request.objects.count()
    requests_pending = Request.objects.filter(status=Request.Status.PENDING).count()
    requests_approved = Request.objects.filter(status=Request.Status.APPROVED).count()
    requests_dispatched = Request.objects.filter(status=Request.Status.DISPATCHED).count()
    requests_rejected = Request.objects.filter(status=Request.Status.REJECTED).count()
    recent_requests = Request.objects.select_related("fulfilled_by").order_by("-created_at")[:6]

    context = {
        "user": request.user,
        "users_total": users_total,
        "users_by_role": users_by_role,
        "recent_users": recent_users,
        "shelters_total": shelters_total,
        "shelter_capacity_total": shelter_capacity_total,
        "shelter_occupancy_total": shelter_occupancy_total,
        "shelters_open": shelters_open,
        "shelters_full": shelters_full,
        "shelters_closed": shelters_closed,
        "recent_shelters": recent_shelters,
        "incidents_total": incidents_total,
        "incidents_active": incidents_active,
        "incidents_critical": incidents_critical,
        "recent_incidents": recent_incidents,
        "volunteers_total": volunteers_total,
        "volunteers_available": volunteers_available,
        "volunteers_deployed": volunteers_deployed,
        "volunteers_unavailable": volunteers_unavailable,
        "recent_volunteers": recent_volunteers,
        "warehouses_total": warehouses_total,
        "inventory_items_total": inventory_items_total,
        "total_stock_units": total_stock_units,
        "warehouses_list": warehouses_list,
        "requests_total": requests_total,
        "requests_pending": requests_pending,
        "requests_approved": requests_approved,
        "requests_dispatched": requests_dispatched,
        "requests_rejected": requests_rejected,
        "recent_requests": recent_requests,
    }
    return render(request, "accounts/dashboard_admin.html", context)


@role_required(User.Role.COORDINATOR)
def dashboard_coordinator(request):
    """Coordinator dashboard endpoint - integrates with warehouse & requests."""
    try:
        from requests_app.dashboard import dashboard as coord_dashboard
        return coord_dashboard(request)
    except Exception:
        return render(
            request,
            "accounts/dashboard_coordinator.html",
            {
                "user": request.user,
                "role_title": "Warehouse Coordinator",
            },
        )


@role_required(User.Role.SHELTER_MANAGER)
def dashboard_shelter_manager(request):
    """Shelter Manager dashboard delegating to shelters app implementation."""
    from shelters.views import shelter_manager_dashboard
    return shelter_manager_dashboard(request)


@role_required(User.Role.VOLUNTEER)
def dashboard_volunteer(request):
    """Volunteer dashboard delegating to volunteers app implementation."""
    from volunteers.views import volunteer_dashboard
    return volunteer_dashboard(request)


@role_required(User.Role.ADMIN)
def admin_create_account(request):
    """Admin-only onboarding interface to create Coordinator and Shelter Manager accounts."""
    from .forms import AdminAccountCreationForm

    if request.method == "POST":
        form = AdminAccountCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"Successfully created {user.get_role_display()} account for '{user.username}'.",
            )
            return redirect("dashboard_admin")
        else:
            messages.error(request, "Please correct the errors indicated below.")
    else:
        form = AdminAccountCreationForm()

    return render(request, "accounts/admin_create_account.html", {"form": form})
