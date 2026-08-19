# b/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Notification

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        if self.user.is_authenticated:
            self.room_group_name = f'user_{self.user.id}'
            
            # Join user's notification group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        pass

    async def notification_message(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
            'link': event.get('link', ''),
            'created_at': event.get('created_at', '')
        }))

    async def assignment_update(self, event):
        # Send assignment update
        await self.send(text_data=json.dumps({
            'type': 'assignment_update',
            'patient_id': event['patient_id'],
            'patient_name': event['patient_name'],
            'action': event['action'],
            'role': event['role']
        }))