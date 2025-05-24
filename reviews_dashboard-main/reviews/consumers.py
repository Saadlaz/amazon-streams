import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ReviewConsumer(AsyncWebsocketConsumer):
    group_name = "reviews"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def broadcast_review(self, event):
        # event == {"type": "broadcast.review", "payload": {...}}
        await self.send(text_data=json.dumps(event["payload"]))
