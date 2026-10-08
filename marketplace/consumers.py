import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message, User, Property

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

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
        message_text = data['message']
        sender_id = data['sender_id']

        # Save message to database asynchronously
        await self.save_message(self.room_id, sender_id, message_text)

        # Broadcast live to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender_id': sender_id
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id']
        }))

    @database_sync_to_async
    def save_message(self, room_id, sender_id, text):
        print("\n=== 🐍 DJANGO CONSUMER DATABASE DATABASE SAVE AUDIT ===")
        print(f"▶️ Received raw room_id string from Flutter: {room_id}")
        print(f"▶️ Received raw sender_id from Flutter: {sender_id}")
        print(f"▶️ Text payload body: '{text}'")
        
        try:
            sender = User.objects.get(id=int(sender_id))
            print(f"✅ Found matching Sender User row: {sender.username}")
            
            # Check if an explicit ChatRoom exists matching this ID integer
            try:
                room = ChatRoom.objects.get(id=int(room_id))
                print(f"✅ Found existing ChatRoom ID row match: {room.id}")
            except (ChatRoom.DoesNotExist, ValueError):
                print(f"⚠️ ChatRoom matching ID {room_id} not found. Treating as Property ID instead...")
                
                # Fetch target property listing entry row configuration parameters
                property_obj = Property.objects.get(id=int(room_id))
                print(f"✅ Located target Property listing: '{property_obj.title}' owned by landlord ID: {property_obj.landlord.id}")
                
                # Dynamic student assignment context parameter verification checks
                scope_user = self.scope.get("user")
                if scope_user and scope_user.is_authenticated and scope_user.role == 'student':
                    student_obj = scope_user
                else:
                    # Fallback to current sender context if connection token handshake isn't synchronized
                    student_obj = sender if sender.role == 'student' else User.objects.filter(role='student').first()
                
                print(f"👤 Binding conversation to Student target row profile: {student_obj.username}")
                
                # Atomically resolve or create the Room framework map parameters
                room, created = ChatRoom.objects.get_or_create(
                    property=property_obj,
                    student=student_obj,
                    landlord=property_obj.landlord
                )
                print(f"📦 ChatRoom target model state: ('Created' status index parameter = {created}) with assigned unique table primary ID: {room.id}")

            # Commit the text directly into database permanent storage rows
            new_msg = Message.objects.create(room=room, sender=sender, text=text)
            print(f"🚀 SUCCESS! Message successfully committed to database storage row ID: {new_msg.id}")
            print("======================================================\n")
            return new_msg
            
        except Exception as e:
            print(f"❌ CRITICAL DATABASE REJECTION EXCEPTION ERROR BLOCK: {str(e)}")
            print("======================================================\n")
            return None
