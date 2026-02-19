import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'video_call_{self.room_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that a new peer joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'peer_joined',
                'peer_id': str(uuid.uuid4()),
                'message': 'A new peer has joined the room'
            }
        )
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others that peer left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'peer_left',
                'message': 'A peer has left the room'
            }
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'offer':
            # Broadcast offer to all other peers in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_offer',
                    'offer': data.get('offer'),
                    'sender': self.channel_name,
                }
            )
        
        elif message_type == 'answer':
            # Broadcast answer to all other peers in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_answer',
                    'answer': data.get('answer'),
                    'sender': self.channel_name,
                }
            )
        
        elif message_type == 'ice-candidate':
            # Broadcast ICE candidate to all other peers
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_ice_candidate',
                    'candidate': data.get('candidate'),
                    'sender': self.channel_name,
                }
            )
        
        elif message_type == 'join':
            # Handle join message
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'user_type': data.get('user_type'),  # 'doctor' or 'patient'
                    'user_name': data.get('user_name'),
                }
            )
        
        elif message_type == 'leave':
            # Handle leave message
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user_type': data.get('user_type'),
                    'user_name': data.get('user_name'),
                }
            )
        
        elif message_type == 'chat':
            # Handle in-call chat message
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data.get('message'),
                    'sender': data.get('sender'),
                    'timestamp': timezone.now().isoformat(),
                }
            )
        
        elif message_type == 'screen-share':
            # Handle screen sharing status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'screen_share_status',
                    'is_sharing': data.get('is_sharing'),
                    'sender': self.channel_name,
                }
            )
    
    # Handler methods for different message types
    async def webrtc_offer(self, event):
        # Don't send back to the sender
        if event['sender'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
            }))
    
    async def webrtc_answer(self, event):
        # Don't send back to the sender
        if event['sender'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
            }))
    
    async def webrtc_ice_candidate(self, event):
        # Don't send back to the sender
        if event['sender'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'ice-candidate',
                'candidate': event['candidate'],
            }))
    
    async def peer_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'peer-joined',
            'peer_id': event.get('peer_id'),
            'message': event.get('message'),
        }))
    
    async def peer_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'peer-left',
            'message': event.get('message'),
        }))
    
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user-joined',
            'user_type': event.get('user_type'),
            'user_name': event.get('user_name'),
        }))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user-left',
            'user_type': event.get('user_type'),
            'user_name': event.get('user_name'),
        }))
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event.get('message'),
            'sender': event.get('sender'),
            'timestamp': event.get('timestamp'),
        }))
    
    async def screen_share_status(self, event):
        # Don't send back to the sender
        if event['sender'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'screen-share',
                'is_sharing': event.get('is_sharing'),
            }))
