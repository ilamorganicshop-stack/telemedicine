import asyncio
import json
import uuid
from collections import defaultdict

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import Appointment, ChatMessage


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'video_call_{self.room_id}'
        self.peer_id = str(uuid.uuid4())
        self.user_type = None  # Will be set when user sends join message
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Don't send peer_joined here - wait for user to send join message
        # This ensures we know their user_type before notifying others
    
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
        print(f"[VideoCall] Received message in room {self.room_id}: {text_data}")
        data = json.loads(text_data)
        message_type = data.get('type')
        print(f"[VideoCall] Message type: {message_type}, from channel: {self.channel_name}")
        
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
            # Store user type
            self.user_type = data.get('user_type')
            
            # Send peer_joined first (generic notification)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'peer_joined',
                    'peer_id': self.peer_id,
                    'sender': self.channel_name,
                    'message': 'A new peer has joined the room'
                }
            )
            
            # Then send user_joined with specific user_type info - notify OTHERS only
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'user_type': data.get('user_type'),  # 'doctor' or 'patient'
                    'user_name': data.get('user_name'),
                    'sender': self.channel_name,
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
                    'sender': self.channel_name,
                }
            )
        
        elif message_type == 'call-ended':
            # Handle call ended - notify all users to close their modals
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_ended',
                    'user_type': data.get('user_type'),
                    'user_name': data.get('user_name'),
                    'sender': self.channel_name,
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
            print(f"[VideoCall] Sending offer to {self.channel_name}")
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
            }))
        else:
            print(f"[VideoCall] Skipping offer for sender {self.channel_name}")
    
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
        # Don't send back to the sender
        if event.get('sender') != self.channel_name:
            print(f"[VideoCall] Sending peer_joined to {self.channel_name}")
            await self.send(text_data=json.dumps({
                'type': 'peer-joined',
                'peer_id': event.get('peer_id'),
                'message': event.get('message'),
            }))
        else:
            print(f"[VideoCall] Skipping peer_joined for sender {self.channel_name}")
    
    async def peer_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'peer-left',
            'message': event.get('message'),
        }))
    
    async def user_joined(self, event):
        # Don't send back to the sender
        if event.get('sender') != self.channel_name:
            print(f"[VideoCall] Sending user_joined ({event.get('user_type')}) to {self.channel_name}")
            await self.send(text_data=json.dumps({
                'type': 'user-joined',
                'user_type': event.get('user_type'),
                'user_name': event.get('user_name'),
            }))
        else:
            print(f"[VideoCall] Skipping user_joined for sender {self.channel_name}")
    
    async def user_left(self, event):
        # Don't send back to the sender
        if event.get('sender') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'user-left',
                'user_type': event.get('user_type'),
                'user_name': event.get('user_name'),
            }))
    
    async def call_ended(self, event):
        # Send to ALL users including sender so both modals close
        await self.send(text_data=json.dumps({
            'type': 'call-ended',
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


class CallInviteConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        self.user = user
        self.appointment_id = int(self.scope['url_route']['kwargs']['appointment_id'])
        self.room_group_name = f'call_invite_{self.appointment_id}'

        appointment = await self.get_appointment(self.appointment_id)
        if not appointment:
            await self.close(code=4004)
            return

        if self.user.id not in {appointment.patient_id, appointment.doctor_id}:
            await self.close(code=4003)
            return

        self.appointment = appointment
        self.is_doctor = self.user.id == appointment.doctor_id
        self.is_patient = self.user.id == appointment.patient_id

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid payload.',
            }))
            return

        message_type = data.get('type')
        if message_type not in {
            'call_invite',
            'call_accepted',
            'call_declined',
            'call_cancelled',
            'call_ended',
        }:
            return

        if message_type == 'call_invite' and not self.is_doctor:
            return

        if message_type in {'call_accepted', 'call_declined'} and not self.is_patient:
            return

        room_id = data.get('room_id') or self.appointment.video_call_room_id
        payload = {
            'type': message_type,
            'appointment_id': self.appointment_id,
            'room_id': room_id,
            'sender_id': self.user.id,
            'sender_role': 'doctor' if self.is_doctor else 'patient',
            'sender_name': self.get_user_display_name(),
            'timestamp': timezone.now().isoformat(),
        }

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'call_event',
                'sender_channel': self.channel_name,
                'payload': payload,
            }
        )

    async def call_event(self, event):
        if event.get('sender_channel') == self.channel_name:
            return

        await self.send(text_data=json.dumps(event.get('payload', {})))

    def get_user_display_name(self):
        full_name = f'{self.user.first_name} {self.user.last_name}'.strip()
        return full_name or self.user.username or self.user.email

    @database_sync_to_async
    def get_appointment(self, appointment_id):
        return Appointment.objects.filter(id=appointment_id).first()


class ChatConsumer(AsyncWebsocketConsumer):
    room_connections = defaultdict(lambda: defaultdict(set))
    presence_lock = None

    @classmethod
    def get_presence_lock(cls):
        if cls.presence_lock is None:
            cls.presence_lock = asyncio.Lock()
        return cls.presence_lock

    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        self.user = user
        self.appointment_id = int(self.scope['url_route']['kwargs']['appointment_id'])
        self.room_group_name = f'chat_{self.appointment_id}'

        appointment = await self.get_appointment(self.appointment_id)
        if not appointment:
            await self.close(code=4004)
            return

        if self.user.id not in {appointment.patient_id, appointment.doctor_id}:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        online_user_ids = await self.add_online_user()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'presence_update',
                'online_user_ids': online_user_ids,
            }
        )

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return

        online_user_ids = await self.remove_online_user()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'presence_update',
                'online_user_ids': online_user_ids,
            }
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid payload.',
            }))
            return

        message_type = data.get('type')

        if message_type == 'message':
            raw_message = data.get('message', '')
            message_text = raw_message.strip()
            if not message_text:
                return

            message_data = await self.save_message(
                appointment_id=self.appointment_id,
                sender_id=self.user.id,
                message_text=message_text,
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    **message_data,
                    'sender_name': self.get_user_display_name(),
                }
            )

        elif message_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_update',
                    'sender_id': self.user.id,
                    'sender_name': self.get_user_display_name(),
                    'is_typing': bool(data.get('is_typing')),
                    'sender_channel': self.channel_name,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event.get('id'),
            'message': event.get('message'),
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'created_at': event.get('created_at'),
            'created_at_display': event.get('created_at_display'),
            'has_attachment': event.get('has_attachment', False),
            'attachment_url': event.get('attachment_url'),
            'attachment_name': event.get('attachment_name'),
            'attachment_size': event.get('attachment_size'),
            'is_image': event.get('is_image', False),
            'is_self': event.get('sender_id') == self.user.id,
        }))

    async def typing_update(self, event):
        if event.get('sender_channel') == self.channel_name:
            return

        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'is_typing': event.get('is_typing', False),
        }))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'online_user_ids': event.get('online_user_ids', []),
        }))

    async def add_online_user(self):
        lock = self.get_presence_lock()
        async with lock:
            room_state = self.room_connections[self.room_group_name]
            room_state[self.user.id].add(self.channel_name)
            return sorted(room_state.keys())

    async def remove_online_user(self):
        lock = self.get_presence_lock()
        async with lock:
            room_state = self.room_connections.get(self.room_group_name)
            if not room_state:
                return []

            user_connections = room_state.get(self.user.id)
            if user_connections:
                user_connections.discard(self.channel_name)
                if not user_connections:
                    room_state.pop(self.user.id, None)

            if not room_state:
                self.room_connections.pop(self.room_group_name, None)
                return []

            return sorted(room_state.keys())

    def get_user_display_name(self):
        full_name = f'{self.user.first_name} {self.user.last_name}'.strip()
        return full_name or self.user.username or self.user.email

    @database_sync_to_async
    def get_appointment(self, appointment_id):
        return Appointment.objects.filter(id=appointment_id).first()

    @database_sync_to_async
    def save_message(self, appointment_id, sender_id, message_text):
        message = ChatMessage.objects.create(
            appointment_id=appointment_id,
            sender_id=sender_id,
            message=message_text,
        )
        local_timestamp = timezone.localtime(message.created_at)

        return {
            'id': message.id,
            'message': message.message,
            'sender_id': sender_id,
            'created_at': local_timestamp.isoformat(),
            'created_at_display': local_timestamp.strftime('%I:%M %p').lstrip('0'),
            'has_attachment': False,
            'attachment_url': None,
            'attachment_name': None,
            'attachment_size': 0,
            'is_image': False,
        }
