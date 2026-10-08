from rest_framework import viewsets, permissions, filters, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Property, Room, ChatRoom, Message
from .serializers import (
    PropertySerializer, 
    RoomSerializer, 
    RegisterSerializer, 
    CustomTokenObtainPairSerializer,
    ChatRoomSerializer,
    MessageSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Handles user login POST requests and issues JWT Access/Refresh tokens.
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": getattr(user, 'role', 'student')
            }
        }, status=status.HTTP_201_CREATED)


class IsLandlordOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow landlords to edit/create properties.
    """
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
        if max_distance:
            queryset = queryset.filter(distance_from_campus_km__lte=float(max_distance))
        return queryset


# marketplace/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Room, RoomImage, Property
from .serializers import RoomSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsLandlordOrReadOnly]

    # 🔍 CRUCIAL MULTIPART FIX: Intercept the incoming image byte streams!
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()

        # Check if an image file was sent in the Multipart request payload keys
        uploaded_file = request.FILES.get('image')
        
        if uploaded_file:
            print(f"\n📸 [DJANGO IMAGE INTERCEPTOR] Found uploaded file asset: {uploaded_file.name}")
            # Atomically build the child row record in the RoomImage table!
            room_image = RoomImage.objects.create(room=room, image=uploaded_file)
            print(f"🚀 [DJANGO IMAGE INTERCEPTOR] Saved to database under row ID: {room_image.id}\n")
        else:
            print("\n⚠️ [DJANGO IMAGE INTERCEPTOR] Warning: No file payload found under key name 'image'\n")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        queryset = super().get_queryset()
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(rent_price__lte=float(max_price))
        return queryset



class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'student':
            return ChatRoom.objects.filter(student=user).order_by('-created_at')
        return ChatRoom.objects.filter(landlord=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

  # marketplace/views.py

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        try:
            # 1. First, try to fetch the room by its direct ChatRoom Primary Key ID
            try:
                room = ChatRoom.objects.get(id=int(pk))
            except (ChatRoom.DoesNotExist, ValueError):
                # 2. FALLBACK DETECTOR: If not found, treat 'pk' as the Property ID
                # and look up the active conversation row for the logged-in user!
                user = request.user
                if getattr(user, 'role', None) == 'student':
                    room = ChatRoom.objects.get(property_id=int(pk), student=user)
                else:
                    room = ChatRoom.objects.get(property_id=int(pk), landlord=user)

            # 3. Pull down the actual historical logs linked to that conversation row
            messages = room.messages.all().order_by('timestamp')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)

        except Exception:
            # If no chat room record exists yet on either lookup path, return an empty array
            return Response([])

