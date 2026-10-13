from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('landlord', 'Landlord'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Property(models.Model):
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    title = models.CharField(max_length=255)
    description = models.TextField()
    address = models.CharField(max_length=255)
    
    # Coordinates for mapping (FloatFields work perfectly for Flutter/React Native integration)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Distance helper (can be dynamically updated or calculated manually)
    distance_from_campus_km = models.FloatField(help_text="Distance to the nearest campus in kilometers")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Room(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=50)
    rent_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    amenities = models.TextField(help_text="Comma separated list e.g., WiFi, Bed, Wardrobe", blank=True)

    def __str__(self):
        return f"{self.property.title} - Room {self.room_number}"

class RoomImage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='room_pics/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


# marketplace/models.py

class ChatRoom(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_chats')
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, related_name='landlord_chats')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'landlord', 'property')

    def __str__(self):
        return f"Chat re: {self.property.title} between {self.student.username} and {self.landlord.username}"

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username}: {self.text[:20]}"


# 7. 🔍 FIXED COMPILATION ORDER: BOOKING REQUEST MAP AT THE ABSOLUTE BOTTOM
class BookingRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_bookings')
    room_number = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
