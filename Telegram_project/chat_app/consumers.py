from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import json


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        print(f"[WS] User {self.user.id} connecting to chat {self.chat_id}")
        
        self.room_group_name = f"chat_{self.chat_id}"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"[WS] User {self.user.id} connected to chat {self.chat_id}")
        
        await self.update_user_status(True)
        await self.broadcast_online_status(True)
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user:
            await self.update_user_status(False)
            await self.broadcast_online_status(False)
        
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'register':
                pass
            
            elif message_type == 'chat_message':
                chat_id = data.get('chat_id')
                content = data.get('content', '')
                attachment_url = data.get('attachment_url')
                attachment_type = data.get('attachment_type')
                
                message = await self.save_message(
                    chat_id, content, attachment_url, attachment_type
                )
                
                if message:
                    print(f"[MSG] Broadcasting message to chat_{chat_id}")
                    await self.channel_layer.group_send(
                        f"chat_{chat_id}",
                        {
                            'type': 'chat_message',
                            'message': {
                                'id': message.id,
                                'chat_id': chat_id,
                                'content': content,
                                'sender': self.user.username,
                                'sender_id': self.user.id,
                                'attachment_url': attachment_url,
                                'attachment_type': attachment_type,
                                'status': message.status,
                                'created_at': message.created_at.strftime('%H:%M'),
                            }
                        }
                    )
            
            elif message_type == 'call_invite':
                to_user_id = data.get('to_user_id')
                call_type = data.get('call_type')
                from_username = data.get('from_username')
                chat_id = data.get('chat_id')
                
                print(f"[CALL] call_invite from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'call_invite',
                        'call_type': call_type,
                        'from_username': from_username,
                        'from_user_id': self.user.id,
                    }
                )
            
            elif message_type == 'call_accept':
                to_user_id = data.get('to_user_id')
                chat_id = data.get('chat_id')
                
                print(f"[CALL] call_accept from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'call_accept',
                        'from_user_id': self.user.id,
                    }
                )
            
            elif message_type == 'call_reject':
                to_user_id = data.get('to_user_id')
                chat_id = data.get('chat_id')
                
                print(f"[CALL] call_reject from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'call_reject',
                        'from_user_id': self.user.id,
                    }
                )
            
            elif message_type == 'call_end':
                to_user_id = data.get('to_user_id')
                chat_id = data.get('chat_id')
                
                print(f"[CALL] call_end from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'call_end',
                        'from_user_id': self.user.id,
                    }
                )
            
            elif message_type == 'offer':
                to_user_id = data.get('to_user_id')
                chat_id = data.get('chat_id')
                offer = data.get('offer')
                
                print(f"[CALL] offer from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'offer',
                        'offer': offer,
                        'from_user_id': self.user.id,
                    }
                )
            
            elif message_type == 'answer':
                to_user_id = data.get('to_user_id')
                chat_id = data.get('chat_id')
                answer = data.get('answer')
                
                print(f"[CALL] answer from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'answer',
                        'answer': answer,
                        'from_user_id': self.user.id,
                    }
                )
            
            elif message_type == 'ice_candidate':
                to_user_id = data.get('to_user_id')
                chat_id = data.get('chat_id')
                candidate = data.get('candidate')
                
                print(f"[CALL] ice_candidate from user {self.user.id} to user {to_user_id} in chat {chat_id}")
                
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        'type': 'call_signal',
                        'signal_type': 'ice_candidate',
                        'candidate': candidate,
                        'from_user_id': self.user.id,
                    }
                )
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    async def chat_message(self, event):
        message = event['message']
        await self.mark_message_delivered(message['id'])
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
        }))
    
    @database_sync_to_async
    def mark_message_delivered(self, message_id):
        from chat_app.models import Message
        try:
            message = Message.objects.get(id=message_id)
            if message.sender_id != self.user.id:
                message.mark_as_delivered()
        except:
            pass
    
    async def call_signal(self, event):
        signal_type = event['signal_type']
        
        print(f"[CALL SIGNAL] {signal_type} from {event.get('from_user_id')} to {self.user.id}")
        
        if signal_type == 'call_invite':
            await self.send(text_data=json.dumps({
                'type': 'call_invite',
                'call_type': event.get('call_type'),
                'from_username': event.get('from_username'),
                'from_user_id': event.get('from_user_id'),
            }))
        elif signal_type == 'call_accept':
            await self.send(text_data=json.dumps({
                'type': 'call_accept',
                'from_user_id': event.get('from_user_id'),
            }))
        elif signal_type == 'call_reject':
            await self.send(text_data=json.dumps({
                'type': 'call_reject',
                'from_user_id': event.get('from_user_id'),
            }))
        elif signal_type == 'call_end':
            await self.send(text_data=json.dumps({
                'type': 'call_end',
                'from_user_id': event.get('from_user_id'),
            }))
        elif signal_type == 'offer':
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event.get('offer'),
                'from_user_id': event.get('from_user_id'),
            }))
        elif signal_type == 'answer':
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event.get('answer'),
                'from_user_id': event.get('from_user_id'),
            }))
        elif signal_type == 'ice_candidate':
            await self.send(text_data=json.dumps({
                'type': 'ice_candidate',
                'candidate': event.get('candidate'),
                'from_user_id': event.get('from_user_id'),
            }))
    
    @database_sync_to_async
    def save_message(self, chat_id, content, attachment_url, attachment_type):
        from chat_app.models import Chat, Message
        try:
            chat = Chat.objects.get(id=chat_id, participants=self.user)
            message = Message.objects.create(
                chat=chat,
                sender=self.user,
                content=content,
                attachment=attachment_url
            )
            if attachment_url:
                message.attachment_type = attachment_type
                message.save()
            
            chat.updated_at = timezone.now()
            chat.save()
            return message
        except:
            return None
    
    @database_sync_to_async
    def get_chat_participants(self, chat_id):
        from chat_app.models import Chat
        try:
            chat = Chat.objects.get(id=chat_id)
            return list(chat.participants.values_list('id', flat=True))
        except:
            return []
    
    @database_sync_to_async
    def update_user_status(self, is_online):
        self.user.is_online = is_online
        if not is_online:
            self.user.last_seen = timezone.now()
        self.user.save()
        return self.user.id
    
    async def broadcast_online_status(self, is_online):
        user_id = self.user.id
        username = self.user.username
        last_seen = self.user.last_seen.strftime('%Y-%m-%d %H:%M:%S') if self.user.last_seen else None
        
        from chat_app.models import Chat
        chats = await database_sync_to_async(
            lambda: list(Chat.objects.filter(participants__id=user_id))
        )()
        
        print(f"[STATUS] Broadcasting online status for user {user_id} to {len(chats)} chats")
        
        for chat in chats:
            print(f"[STATUS] Sending to chat_{chat.id}")
            await self.channel_layer.group_send(
                f"chat_{chat.id}",
                {
                    'type': 'user_status',
                    'user_id': user_id,
                    'username': username,
                    'is_online': is_online,
                    'last_seen': last_seen
                }
            )
    
    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_online_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online'],
            'last_seen': event.get('last_seen')
        }))
