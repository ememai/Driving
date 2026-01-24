# yourapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        self.room_group_name = f'dashboard_notifications_{self.user.id}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
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

    async def send_unverified_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'unverified',
            'unverified': event['unverified']
        }))
