from django.contrib import admin
from .models import User, Profile, Chat, Message, GroupMember

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'is_online', 'is_staff', 'date_joined']
    list_filter = ['is_online', 'is_staff', 'is_active']
    search_fields = ['username', 'email']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'city', 'country']
    search_fields = ['user__username', 'phone_number']

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'is_ai_chat', 'created_at']
    list_filter = ['type', 'is_ai_chat']
    search_fields = ['name']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'sender', 'content', 'status', 'created_at']
    list_filter = ['status', 'is_ai_message', 'is_deleted']
    search_fields = ['content', 'sender__username']
    date_hierarchy = 'created_at'

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['group', 'user', 'role', 'joined_at']
    list_filter = ['role']
