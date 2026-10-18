from django.db import transaction
from django.shortcuts import get_object_or_404
from warehouses.models import InventoryItem
from .models import Request


@transaction.atomic
def approve_request(request_id, warehouse_id):
    req = get_object_or_404(Request, pk=request_id)

    item = InventoryItem.objects.select_for_update().get(
        warehouse_id=warehouse_id,
        item_name=req.item_name
    )

    if item.quantity < req.quantity:
        raise ValueError("Not enough stock to fulfill this request")

    item.quantity -= req.quantity
    item.save()

    req.status = Request.Status.APPROVED
    req.fulfilled_by_id = warehouse_id
    req.save()

    return req
