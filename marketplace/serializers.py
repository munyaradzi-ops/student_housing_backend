# marketplace/views.py
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Property, Room, RoomImage, ChatRoom, Message
from .serializers import (
    PropertySerializer, 
    RoomSerializer, 
    RegisterSerializer, 
    CustomTokenObtainPairSerializer,
    ChatRoomSerializer,
    MessageSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class IsLandlordOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'landlord'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.landlord == request.user

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all().order_by('-created_at')
    serializer_class = PropertySerializer
    permission_classes = [IsLandlordOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(landlord=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        max_distance = self.request.query_params.get('max_distance')
        max_price = self.request.query_params.get('max_price')
        
        if max_distance:
            queryset = queryset.filter(distance_from_campus_km__lte=float(max_distance))
        if max_price:
            queryset = queryset.filter(rooms__rent_price__lte=float(max_price)).distinct()
        return queryset

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsLandlordOrReadOnly]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()

        # 🔍 BULK MULTIPART INTERCEPTOR LOOP
        # Iterates over each file stream attached to the 'image' form-data key
        uploaded_files = request.FILES.getlist('image')
        for file_asset in uploaded_files:
            RoomImage.objects.create(room=room, image=file_asset)
            print(f"📸 Saved image file asset: {file_asset.name}")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'student':
            return ChatRoom.objects.filter(student=user).order_by('-created_at')
        return ChatRoom.objects.filter(landlord=user).order_by('-created_at')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        try:
            try:
                room = ChatRoom.objects.get(id=int(pk))
            except (ChatRoom.DoesNotExist, ValueError):
                user = request.user
                if getattr(user, 'role', None) == 'student':
                    room = ChatRoom.objects.get(property_id=int(pk), student=user)
                else:
                    room = ChatRoom.objects.get(property_id=int(pk), landlord=user)

            messages = room.messages.all().order_by('timestamp')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])
