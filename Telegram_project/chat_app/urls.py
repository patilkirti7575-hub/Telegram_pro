from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('settings/', views.settings_view, name='settings'),
    path('settings/password/', views.change_password_view, name='change_password'),
    path('settings/delete-account/', views.delete_account_view, name='delete_account'),
    
    path('chats/', views.chat_list_view, name='chat_list'),
    path('chat/<int:chat_id>/', views.chat_view, name='chat_view'),
    path('chat/start/<int:user_id>/', views.start_chat_view, name='start_chat'),
    path('chat/ai/', views.ai_chat_view, name='ai_chat'),
    path('chat/ai/message/', views.ai_chat_message, name='ai_chat_message'),
    
    path('message/delete/<int:message_id>/', views.delete_message, name='delete_message'),
    path('messages/new/<int:chat_id>/', views.get_new_messages, name='get_new_messages'),
    path('messages/seen/<int:chat_id>/', views.mark_messages_seen, name='mark_messages_seen'),
    path('messages/status/<int:chat_id>/', views.get_message_status, name='get_message_status'),
    
    path('search/', views.search_users, name='search_users'),
    path('profile/', views.profile_view, name='profile'),
    
    # Status URLs
    path('status/', views.status_list_view, name='status_list'),
    path('status/create/', views.status_create_view, name='status_create'),
    path('status/view/<int:user_id>/', views.status_viewer_view, name='status_viewer'),
    path('status/delete/<int:status_id>/', views.status_delete_view, name='status_delete'),
    path('status/reply/<int:status_id>/', views.status_reply_view, name='status_reply'),
    path('status/viewers/', views.my_status_viewers_view, name='my_status_viewers'),
]
