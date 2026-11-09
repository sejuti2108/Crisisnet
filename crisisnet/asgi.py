import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crisisnet.settings")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
import crisisnet.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(crisisnet.routing.websocket_urlpatterns),
})