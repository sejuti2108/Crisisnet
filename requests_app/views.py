from django.db import transaction
from django.shortcuts import get_object_or_404
from warehouses.models import InventoryItem
from .models import Request


@transaction.atomic
def approve_request(request_id, warehouse_id):
    req = Request.objects.select_for_update().get(pk=request_id)

    if req.status != Request.Status.PENDING:
        raise ValueError("Only pending requests can be approved")

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


@transaction.atomic
def reject_request(request_id):
    req = Request.objects.select_for_update().get(pk=request_id)

    if req.status != Request.Status.PENDING:
        raise ValueError("Only pending requests can be rejected")

    req.status = Request.Status.REJECTED
    req.save()
    return req


@transaction.atomic
def dispatch_request(request_id):
    req = Request.objects.select_for_update().get(pk=request_id)

    if req.status != Request.Status.APPROVED:
        raise ValueError("Only approved requests can be dispatched")

    req.status = Request.Status.DISPATCHED
    req.save()
    return req