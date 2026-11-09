import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class AlertBroadcastConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time incident alerts and operational bulletins.
    Active web clients (dashboards, map, incident pages) connect here to receive
    live pushes without polling.
    """

    async def connect(self):
        self.group_name = "alerts"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps({
                "event_type": "connected",
                "message": "Connected to CrisisNet Live Alerts Broadcast feed.",
            })
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def alert_broadcast(self, event):
        """
        Handler for messages sent from channel_layer.group_send("alerts", ...)
        """
        await self.send(text_data=json.dumps(event["data"]))
