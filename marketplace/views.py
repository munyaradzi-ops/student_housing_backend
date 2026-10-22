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

      # This explicitly ensures PATCH requests process smoothly without requiring ALL model fields
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        max_distance = self.request.query_params.get('max_distance')
        if max_distance:
            queryset = queryset.filter(distance_from_campus_km__lte=float(max_distance))
        return queryset


# marketplace/views.py
from .models import BookingRequest
from .serializers import BookingRequestSerializer

class BookingRequestViewSet(viewsets.ModelViewSet):
    queryset = BookingRequest.objects.all()
    serializer_class = BookingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'student':
            return BookingRequest.objects.filter(student=user)
        # Landlords can only see bookings targeted at their own properties
        return BookingRequest.objects.filter(property__landlord=user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        booking = self.get_object()
        booking.status = 'accepted'
        booking.save()
        
        # Dynamic Feature: Auto-create a live ChatRoom when request is accepted!
        ChatRoom.objects.get_or_create(
            property=booking.property,
            student=booking.student,
            landlord=booking.property.landlord
        )
        return Response({'status': 'booking accepted, chat workspace established'})



# marketplace/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Room, RoomImage, Property
from .serializers import RoomSerializer

# marketplace/views.py

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsLandlordOrReadOnly]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()

        # 🔍 EXTENDED MULTIPART DATA EXTRACTOR:
        # Tries 'image', 'image[]', and direct FILES lists to capture all uploads safely!
        uploaded_files = request.FILES.getlist('image') or request.FILES.getlist('image[]')
        
        # If files are streamed with index suffix markers (fallback tracking)
        if not uploaded_files:
            uploaded_files = [request.FILES[key] for key in request.FILES if 'image' in key]

        print(f"\n📸 [CLOUD SERVICE] Processing multi-image upload queue...")
        print(f"📦 Total discovered binary files inside request stream: {len(uploaded_files)}")

        for file_asset in uploaded_files:
            room_image = RoomImage.objects.create(room=room, image=file_asset)
            print(f"   ✅ Saved child RoomImage row ID: {room_image.id} | Filename: {file_asset.name}")
        print("======================================================\n")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


        # 🔍 FORCE PARTIAL UPDATE COMPATIBILITY FOR ROOMS:
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        print(f"📥 [CLOUD EDIT] Processing Room PATCH update for ID {kwargs.get('pk')}:", request.data)
        return super().update(request, *args, **kwargs)


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

