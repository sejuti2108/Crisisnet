from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from requests_app.models import Request
from warehouses.models import InventoryItem
from .forms import ShelterOccupancyUpdateForm, ShelterSupplyRequestForm
from .models import Shelter


@role_required(User.Role.SHELTER_MANAGER)
def shelter_manager_dashboard(request):
    """
    Shelter Manager dashboard displaying the manager's authorized shelter,
    capacity & live occupancy, regional stock overview, and supply request pipeline.
    """
    user_shelters = Shelter.objects.filter(manager=request.user)

    selected_shelter_id = request.GET.get("shelter_id")
    current_shelter = None

    if selected_shelter_id:
        # Strict authorization: manager can ONLY view their own shelter
        current_shelter = user_shelters.filter(id=selected_shelter_id).first()
        if not current_shelter and not request.user.is_superuser:
            raise PermissionDenied("You are not authorized to access this shelter.")
    else:
        current_shelter = user_shelters.first()

    requests_history = []
    regional_stock = []
    occupancy_form = None
    request_form = None

    if current_shelter:
        requests_history = Request.objects.filter(
            shelter_name=current_shelter.name
        ).order_by("-created_at")

        regional_stock = InventoryItem.objects.select_related("warehouse").order_by(
            "warehouse__name", "item_name"
        )

        occupancy_form = ShelterOccupancyUpdateForm(shelter=current_shelter)
        request_form = ShelterSupplyRequestForm()

    context = {
        "user_shelters": user_shelters,
        "current_shelter": current_shelter,
        "requests_history": requests_history,
        "regional_stock": regional_stock,
        "occupancy_form": occupancy_form,
        "request_form": request_form,
    }
    return render(request, "shelters/shelter_manager_dashboard.html", context)


@require_POST
@role_required(User.Role.SHELTER_MANAGER)
def update_shelter_occupancy(request, shelter_id):
    """Update current occupancy of the manager's assigned shelter."""
    shelter = get_object_or_404(Shelter, id=shelter_id)

    if shelter.manager != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to modify this shelter.")

    form = ShelterOccupancyUpdateForm(request.POST, shelter=shelter)
    if form.is_valid():
        shelter.current_occupancy = form.cleaned_data["current_occupancy"]
        shelter.save()
        messages.success(
            request,
            f"Occupancy for {shelter.name} updated to {shelter.current_occupancy} / {shelter.capacity} ({shelter.get_status_display()}).",
        )
    else:
        for error in form.errors.values():
            messages.error(request, error.as_text())

    return redirect("dashboard_shelter_manager")


@require_POST
@role_required(User.Role.SHELTER_MANAGER)
def create_supply_request(request, shelter_id):
    """Submit a relief supply request for the manager's assigned shelter."""
    shelter = get_object_or_404(Shelter, id=shelter_id)

    if shelter.manager != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to submit requests for this shelter.")

    form = ShelterSupplyRequestForm(request.POST)
    if form.is_valid():
        new_req = Request.objects.create(
            shelter_name=shelter.name,
            item_name=form.cleaned_data["item_name"],
            quantity=form.cleaned_data["quantity"],
            status=Request.Status.PENDING,
        )
        # Attempt WebSocket broadcast if available
        try:
            from requests_app.views import broadcast_update
            broadcast_update(new_req)
        except Exception:
            pass

        messages.success(
            request,
            f"Relief supply request #{new_req.id} for {new_req.quantity}x '{new_req.item_name}' submitted successfully.",
        )
    else:
        for error in form.errors.values():
            messages.error(request, error.as_text())

    return redirect("dashboard_shelter_manager")
