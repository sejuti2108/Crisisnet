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
    """Admin dashboard endpoint."""
    return render(
        request,
        "accounts/dashboard_admin.html",
        {
            "user": request.user,
            "role_title": "System Administrator",
        },
    )


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
    """Shelter Manager dashboard placeholder (real dashboard implemented in Phase 4)."""
    return render(
        request,
        "accounts/dashboard_shelter_manager.html",
        {
            "user": request.user,
            "role_title": "Shelter Manager",
        },
    )


@role_required(User.Role.VOLUNTEER)
def dashboard_volunteer(request):
    """Volunteer dashboard placeholder (real view implemented in Phase 6)."""
    return render(
        request,
        "accounts/dashboard_volunteer.html",
        {
            "user": request.user,
            "role_title": "Volunteer",
        },
    )


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
