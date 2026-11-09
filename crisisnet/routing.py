from django.urls import path
from requests_app.consumers import RequestConsumer
from incidents.consumers import AlertBroadcastConsumer

websocket_urlpatterns = [
    path("ws/requests/", RequestConsumer.as_asgi()),
    path("ws/alerts/", AlertBroadcastConsumer.as_asgi()),
]
