# marketplace/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    PropertyViewSet, 
    RoomViewSet, 
    ChatRoomViewSet,
    RegisterView, 
     BookingRequestViewSet,
    CustomTokenObtainPairView  # Matching your custom view declaration exactly
)

# Initialize the REST Framework App Router
router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'chats', ChatRoomViewSet, basename='chat')
router.register(r'bookings', BookingRequestViewSet, basename='booking')


urlpatterns = [
    # API viewset query routers (properties, rooms, chats)
    path('', include(router.urls)),
    
    # Decoupled Security Authentication Gateways
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
