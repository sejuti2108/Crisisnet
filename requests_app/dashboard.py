from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from warehouses.models import InventoryItem
from .models import Request
from .views import (
    approve_request,
    reject_request,
    dispatch_request,
    suggest_warehouses,
)


def dashboard(request):
    rows = []
    for r in Request.objects.order_by("-created_at"):
        options = []
        if r.status == Request.Status.PENDING:
            options = suggest_warehouses(r.id)
        rows.append({"req": r, "options": options})

    context = {
        "rows": rows,
        "stock": InventoryItem.objects.select_related("warehouse").order_by(
            "warehouse__name", "item_name"
        ),
    }
    return render(request, "requests_app/dashboard.html", context)


@require_POST
def approve_action(request, request_id):
    warehouse_id = request.POST.get("warehouse")
    if not warehouse_id:
        messages.error(request, "Please choose a warehouse first.")
        return redirect("dashboard")
    try:
        approve_request(request_id, int(warehouse_id))
        messages.success(request, f"Request {request_id} approved.")
    except (ValueError, ObjectDoesNotExist) as e:
        messages.error(request, f"Could not approve request {request_id}: {e}")
    return redirect("dashboard")


@require_POST
def reject_action(request, request_id):
    try:
        reject_request(request_id)
        messages.success(request, f"Request {request_id} rejected.")
    except (ValueError, ObjectDoesNotExist) as e:
        messages.error(request, f"Could not reject request {request_id}: {e}")
    return redirect("dashboard")


@require_POST
def dispatch_action(request, request_id):
    try:
        dispatch_request(request_id)
        messages.success(request, f"Request {request_id} dispatched.")
    except (ValueError, ObjectDoesNotExist) as e:
        messages.error(request, f"Could not dispatch request {request_id}: {e}")
    return redirect("dashboard")