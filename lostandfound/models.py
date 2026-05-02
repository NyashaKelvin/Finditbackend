from django.db import models
from django.contrib.auth.models import User
import sys
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

class Item(models.Model):
    CATEGORY_CHOICES = [
        ('PERSONAL', 'Personal'),
        ('ELECTRONICS', 'Electronics'),
        ('DOCUMENTS', 'Documents'),
        ('CLOTHING', 'Clothing'),
        ('ACADEMIC', 'Academic'),
        ('VALUABLE', 'Valuable'),
        ('MISC', 'Miscellaneous'),
    ]

    STATUS_CHOICES = [
        ('LOST', 'Lost'),
        ('FOUND', 'Found'),
        ('CLAIMED', 'Claimed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='MISC', db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='LOST', db_index=True)
    location = models.CharField(max_length=255)
    image = models.ImageField(upload_to='item_images/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='item_thumbnails/', null=True, blank=True)
    date_spotted = models.DateTimeField()
    verification_question = models.TextField(blank=True, null=True)           
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.title} — {self.location}"

    def save(self, *args, **kwargs):
        if self.image and not self.thumbnail:
            self.thumbnail = self.make_thumbnail(self.image)
        super().save(*args, **kwargs)

    def make_thumbnail(self, image, size=(400, 400)):
        img = Image.open(image)
        # Convert to RGB mode (removes alpha channel) to allow saving as JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(size)
        
        thumb_io = BytesIO()
        img.save(thumb_io, 'JPEG', quality=85)
        
        thumbnail = InMemoryUploadedFile(thumb_io, 'ImageField', "%s_thumb.jpg" % image.name.split('.')[0], 'image/jpeg', sys.getsizeof(thumb_io), None)
        return thumbnail

class ClaimRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='claim_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims_made')
    answer_to_question = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.requester.username} claiming {self.item.title}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    deleted_by_sender = models.BooleanField(default=False)
    deleted_by_receiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"
