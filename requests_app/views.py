from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.http import HttpResponse
from warehouses.models import InventoryItem
from .models import Request


def broadcast_update(req):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        "requests",
        {
            "type": "request_update",
            "data": {
                "id": req.id,
                "shelter": req.shelter_name,
                "item": req.item_name,
                "quantity": req.quantity,
                "status": req.status,
            },
        },
    )


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
    transaction.on_commit(lambda: broadcast_update(req))
    return req


@transaction.atomic
def reject_request(request_id):
    req = Request.objects.select_for_update().get(pk=request_id)

    if req.status != Request.Status.PENDING:
        raise ValueError("Only pending requests can be rejected")

    req.status = Request.Status.REJECTED
    req.save()
    transaction.on_commit(lambda: broadcast_update(req))
    return req


@transaction.atomic
def dispatch_request(request_id):
    req = Request.objects.select_for_update().get(pk=request_id)

    if req.status != Request.Status.APPROVED:
        raise ValueError("Only approved requests can be dispatched")

    req.status = Request.Status.DISPATCHED
    req.save()
    transaction.on_commit(lambda: broadcast_update(req))
    return req


def suggest_warehouses(request_id):
    req = Request.objects.get(pk=request_id)
    return InventoryItem.objects.filter(
        item_name=req.item_name,
        quantity__gte=req.quantity
    ).select_related("warehouse")


def live_test(request):
    html = """
    <h2>Live updates test</h2>
    <ul id="log"></ul>
    <script>
      const ws = new WebSocket("ws://" + window.location.host + "/ws/requests/");
      ws.onmessage = function (e) {
        const li = document.createElement("li");
        li.textContent = e.data;
        document.getElementById("log").appendChild(li);
      };
    </script>
    """
    return HttpResponse(html)


def test_broadcast(request):
    req = Request.objects.create(
        shelter_name="Mirpur Shelter 1", item_name="Blanket", quantity=10
    )
    reject_request(req.id)
    return HttpResponse(f"Created and rejected request {req.id}")