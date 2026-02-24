from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync


class DashboardConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            # deny anonymous
            return self.close()
        self.group_name = f"user_{user.id}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    # handler for events pushed to the group
    def unverified_subscription(self, event):
        # simply forward the event type to client
        self.send_json({"type": "unverified_subscription"})
