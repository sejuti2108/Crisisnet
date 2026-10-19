import json
from channels.generic.websocket import AsyncWebsocketConsumer


class RequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("requests", self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({"message": "Connected to live updates"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("requests", self.channel_name)

    async def request_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))