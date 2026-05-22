from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Extended User model with profile information"""
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-is_online', 'username']

    def __str__(self):
        return self.username


class Profile(models.Model):
    """User profile with additional information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Chat(models.Model):
    """Chat model for both individual and group chats"""
    CHAT_TYPES = [
        ('private', 'Private'),
        ('group', 'Group'),
    ]

    name = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=10, choices=CHAT_TYPES, default='private')
    participants = models.ManyToManyField(User, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_ai_chat = models.BooleanField(default=False)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_chats', null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.type == 'private':
            return f"Chat {self.id}"
        return self.name

    def get_other_participant(self, user):
        """Get the other participant in a private chat"""
        if self.type == 'private':
            return self.participants.exclude(id=user.id).first()
        return None

    def get_display_name(self, user=None):
        """Get display name for the chat"""
        if self.type == 'group':
            return self.name
        other = self.get_other_participant(user)
        return other.username if other else "Unknown"

    def get_last_message(self):
        """Get the last message in the chat"""
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """Message model for chat messages"""
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('seen', 'Seen'),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    attachment_type = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_ai_message = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"

    def mark_as_seen(self):
        """Mark message as seen"""
        if self.status != 'seen':
            self.status = 'seen'
            self.save(update_fields=['status'])

    def mark_as_delivered(self):
        """Mark message as delivered"""
        if self.status == 'sent':
            self.status = 'delivered'
            self.save(update_fields=['status'])


class MessageRead(models.Model):
    """Track read status for messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_messages')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']


class GroupMember(models.Model):
    """Group membership model"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    group = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_muted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        unique_together = ['group', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class Status(models.Model):
    """WhatsApp-like Status model"""
    STATUS_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statuses')
    content_type = models.CharField(max_length=10, choices=STATUS_TYPES, default='text')
    content = models.TextField(blank=True)
    media = models.FileField(upload_to='statuses/', blank=True, null=True)
    background_color = models.CharField(max_length=20, blank=True, default='#128C7E')
    font_color = models.CharField(max_length=20, blank=True, default='#FFFFFF')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username}'s status - {self.content_type}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def view_count(self):
        return self.views.count()
    
    @property
    def viewer_count(self):
        return self.views.filter(viewed=True).count()


class StatusView(models.Model):
    """Track who viewed a status"""
    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    replied = models.BooleanField(default=False)
    reply_content = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['status', 'user']
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.username} viewed {self.status.user.username}'s status"
