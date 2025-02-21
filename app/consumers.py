# yourapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'dashboard_notifications'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({
            'message': data['message']
        }))

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
