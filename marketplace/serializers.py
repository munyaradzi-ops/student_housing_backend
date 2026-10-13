# marketplace/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Property, Room, RoomImage, ChatRoom, Message

User = get_user_model()

# ----------------------------------------------------
# 🔐 AUTHENTICATION & SECURITY SERIALIZERS
# ----------------------------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = getattr(user, 'role', 'student')
        token['id'] = user.id  
        token['username'] = user.username
        return token

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'password', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password) 
        user.save()
        return user

# ----------------------------------------------------
# 🏡 PROPERTY, MARKETPLACE, & HOUSING SERIALIZERS
# ----------------------------------------------------

class RoomImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = RoomImage
        fields = ['id', 'room', 'image', 'image_url', 'uploaded_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            # Cloud/Railway deployment fallback prefix
            return f"https://railway.app{obj.image.url}"
        return None

class RoomSerializer(serializers.ModelSerializer):
    images = RoomImageSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'property', 'room_number', 'rent_price', 'is_available', 'amenities', 'images']

class PropertySerializer(serializers.ModelSerializer):
    landlord = serializers.PrimaryKeyRelatedField(read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'landlord', 'title', 'description', 'address', 
            'latitude', 'longitude', 'distance_from_campus_km', 'rooms', 'created_at'
        ]

# ----------------------------------------------------
# 💬 REAL-TIME MESSAGING LOOP SERIALIZERS
# ----------------------------------------------------

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'sender_username', 'text', 'timestamp']

class ChatRoomSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    landlord_username = serializers.CharField(source='landlord.username', read_only=True)
    property_title = serializers.CharField(source='property.title', read_only=True)
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'student', 'student_username', 'landlord', 
            'landlord_username', 'property', 'property_title', 
            'latest_message', 'created_at'
        ]

    def get_latest_message(self, obj):
        msg = obj.messages.all().order_by('-timestamp').first()
        if msg:
            return MessageSerializer(msg).data
        return None
