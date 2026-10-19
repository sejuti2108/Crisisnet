from django.urls import path
from .consumers import RequestConsumer

websocket_urlpatterns = [
    path("ws/requests/", RequestConsumer.as_asgi()),
]