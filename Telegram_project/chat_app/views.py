from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import User, Chat, Message, Status, StatusView
import json


def home(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    return redirect('login')


# =======================
# AUTHENTICATION
# =======================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            user.is_online = True
            user.save()
            return redirect('chat_list')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'chat_app/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        request.user.is_online = False
        request.user.save()
    logout(request)
    return redirect('login')


# =======================
# SETTINGS
# =======================

@login_required
def settings_view(request):
    user = request.user
    chats = Chat.objects.filter(participants=user).order_by('-updated_at')
    users = User.objects.exclude(id=user.id).order_by('-is_online', 'username')
    
    if request.method == 'POST':
        user.email = request.POST.get('email', user.email)
        user.bio = request.POST.get('bio', '')
        
        avatar = request.FILES.get('avatar')
        if avatar:
            user.avatar = avatar
        
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('settings')
    
    context = {
        'user': user,
        'chats': chats,
        'users': users,
    }
    return render(request, 'chat_app/settings.html', context)


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully!')
        else:
            messages.error(request, 'Please correct the errors below.')
        return redirect('settings')
    return redirect('settings')


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, 'Account deleted successfully.')
        return redirect('login')
    return redirect('settings')


# =======================
# CHAT VIEWS
# =======================

@login_required
def chat_list_view(request):
    user = request.user
    user.is_online = True
    user.last_seen = timezone.now()
    user.save()
    
    chats = Chat.objects.filter(participants=user).order_by('-updated_at')
    users = User.objects.exclude(id=user.id).order_by('-is_online', 'username')
    
    context = {
        'chats': chats,
        'users': users,
    }
    return render(request, 'chat_app/index.html', context)


@login_required
def chat_view(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    users = User.objects.exclude(id=request.user.id).order_by('-is_online', 'username')
    messages_list = chat.messages.filter(is_deleted=False).order_by('created_at')
    
    other_user = chat.get_other_participant(request.user)
    
    if request.method == "POST":
        content = request.POST.get('content', '')
        attachment = request.FILES.get('attachment')
        attachment_url = request.POST.get('attachment_url', '')
        attachment_type = request.POST.get('attachment_type', '')
        reply_to_id = request.POST.get('reply_to', '')
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        is_gif = '[GIF]' in content and '[/GIF]' in content if content else False
        
        if content or attachment or attachment_url:
            msg = Message.objects.create(
                chat=chat,
                sender=request.user,
                content=content,
                attachment=attachment
            )
            
            if attachment:
                if attachment.content_type.startswith('image/'):
                    msg.attachment_type = 'image'
                elif attachment.content_type.startswith('video/'):
                    msg.attachment_type = 'video'
                else:
                    msg.attachment_type = 'file'
                msg.save()
            elif is_gif:
                msg.attachment_type = 'gif'
                msg.save()
            elif attachment_type == 'gif' and attachment_url:
                msg.attachment_type = 'gif'
                msg.save()
            
            chat.updated_at = timezone.now()
            chat.save()
            
            if is_ajax:
                import re
                gif_url = ''
                if is_gif:
                    match = re.search(r'\[GIF\](.*?)\[/GIF\]', content)
                    if match:
                        gif_url = match.group(1)
                
                Message.objects.filter(
                    chat=chat,
                    sender=other_user,
                    status='sent'
                ).update(status='delivered')
                
                response = JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': msg.id,
                        'content': msg.content,
                        'attachment': msg.attachment.url if msg.attachment else None,
                        'attachment_url': gif_url if gif_url else attachment_url,
                        'attachment_type': msg.attachment_type,
                        'sender': msg.sender.username,
                        'sender_id': msg.sender.id,
                        'created_at': msg.created_at.strftime('%H:%M'),
                        'reply_to': reply_to_id if reply_to_id else None,
                        'status': msg.status,
                    }
                })
                response['Content-Type'] = 'application/json; charset=utf-8'
                return response
    
    # Mark messages from other user as delivered when chat is opened
    Message.objects.filter(
        chat=chat,
        sender=other_user,
        status='sent'
    ).update(status='delivered')
    
    context = {
        'chat': chat,
        'messages': messages_list,
        'other_user': other_user,
        'users': users,
    }
    return render(request, 'chat_app/chat.html', context)


@login_required
def ai_chat_view(request):
    users = User.objects.exclude(id=request.user.id).order_by('-is_online', 'username')
    chats = Chat.objects.filter(participants=request.user).order_by('-updated_at')
    
    context = {
        'users': users,
        'chats': chats,
    }
    return render(request, 'chat_app/ai_chat.html', context)


@login_required
@csrf_exempt
def ai_chat_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            if not user_message:
                return JsonResponse({'error': 'Message is required'}, status=400)
            
            ai_response = get_ai_response(user_message, request.user.username)
            
            return JsonResponse({
                'response': ai_response,
                'user_message': user_message,
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def get_ai_response(message, username):
    api_key = settings.OPENAI_API_KEY
    
    if not api_key:
        return get_demo_response(message, username)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Be friendly, concise, and helpful."},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return get_demo_response(message, username)


def get_demo_response(message, username):
    msg_lower = message.lower()
    
    greetings = ['hello', 'hi', 'hey', 'howdy', 'greetings']
    help_words = ['help', 'how', 'what', 'why', 'when', 'where', 'can', 'could']
    thanks = ['thanks', 'thank you', 'thx']
    
    if any(word in msg_lower for word in greetings):
        return f"Hello {username}! How can I help you today? I'm here to answer your questions."
    
    if any(word in msg_lower for word in thanks):
        return "You're welcome! Is there anything else I can help you with?"
    
    if 'how are you' in msg_lower:
        return "I'm doing great! I'm ready to help you with any questions."
    
    if 'your name' in msg_lower:
        return "I'm an AI Assistant! I can help with learning, coding, writing, and more."
    
    if any(word in msg_lower for word in help_words):
        return "I can help you with:\n\nStudy & Learning\nProgramming - Python, Java, JS\nWriting - Essays, emails\nBrainstorming & Ideas\n\nWhat would you like help with?"
    
    if 'joke' in msg_lower:
        return "Here's a joke:\n\nWhy don't scientists trust atoms?\n\nBecause they make up everything!"
    
    if 'code' in msg_lower or 'python' in msg_lower:
        return "I can help you with programming! Tell me what you're working on."
    
    return f"That's interesting, {username}! Could you provide more details so I can help better?"


@login_required
def start_chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    if other_user == request.user:
        return redirect('chat_list')
    
    existing_chat = Chat.objects.filter(
        participants=request.user,
        type='private'
    ).filter(participants=other_user).first()
    
    if existing_chat:
        return redirect('chat_view', chat_id=existing_chat.id)
    
    chat = Chat.objects.create(type='private')
    chat.participants.add(request.user, other_user)
    
    return redirect('chat_view', chat_id=chat.id)


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.is_deleted = True
    message.content = "[Message deleted]"
    message.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('chat_view', chat_id=message.chat.id)


@login_required
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    chat.participants.remove(request.user)
    if chat.participants.count() == 0:
        chat.delete()
    return redirect('chat_list')


@login_required
def search_users(request):
    query = request.GET.get('q', '')
    users = []
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id)[:20]
    
    return render(request, 'chat_app/search.html', {'users': users, 'query': query})


@login_required
def profile_view(request):
    return redirect('settings')


@login_required
def get_new_messages(request, chat_id):
    last_id = int(request.GET.get('last_id', 0))
    try:
        chat = Chat.objects.get(id=chat_id, participants=request.user)
        new_messages = chat.messages.filter(
            id__gt=last_id, is_deleted=False
        ).exclude(sender=request.user).order_by('created_at')
        
        return JsonResponse({
            'messages': [{
                'id': m.id,
                'content': m.content,
                'attachment': m.attachment.url if m.attachment else None,
                'attachment_type': m.attachment_type,
                'sender': m.sender.username,
                'created_at': m.created_at.strftime('%H:%M'),
            } for m in new_messages]
        })
    except:
        return JsonResponse({'messages': []})


# =======================
# STATUS FEATURES
# =======================

@login_required
def status_list_view(request):
    """Display list of all users' statuses"""
    from django.utils import timezone
    
    user = request.user
    chats = Chat.objects.filter(participants=user).order_by('-updated_at')
    users = User.objects.exclude(id=user.id).order_by('-is_online', 'username')
    
    now = timezone.now()
    statuses = Status.objects.filter(
        is_active=True,
        expires_at__gt=now
    ).exclude(user=user).select_related('user')
    
    user_statuses = {}
    for status in statuses:
        if status.user.id not in user_statuses:
            user_statuses[status.user.id] = {
                'user': status.user,
                'statuses': [],
                'has_unseen': False
            }
        user_statuses[status.user.id]['statuses'].append(status)
    
    my_status = Status.objects.filter(user=user, is_active=True, expires_at__gt=now)
    my_status_list = list(my_status)
    
    context = {
        'chats': chats,
        'users': users,
        'user_statuses': user_statuses.values(),
        'my_status': my_status_list,
        'my_status_count': len(my_status_list),
    }
    return render(request, 'chat_app/status_list.html', context)


@login_required
def status_create_view(request):
    """Create a new status"""
    from django.utils import timezone
    
    if request.method == 'POST':
        content_type = request.POST.get('content_type', 'text')
        content = request.POST.get('content', '')
        background_color = request.POST.get('background_color', '#128C7E')
        font_color = request.POST.get('font_color', '#FFFFFF')
        media = request.FILES.get('media')
        
        expires_at = timezone.now() + timezone.timedelta(hours=24)
        
        status = Status.objects.create(
            user=request.user,
            content_type=content_type,
            content=content,
            background_color=background_color,
            font_color=font_color,
            media=media,
            expires_at=expires_at
        )
        
        messages.success(request, 'Status posted successfully!')
        return redirect('status_list')
    
    context = {
        'content_types': Status.STATUS_TYPES,
    }
    return render(request, 'chat_app/status_create.html', context)


@login_required
def status_viewer_view(request, user_id=None):
    """View someone's status"""
    from django.utils import timezone
    
    target_user = get_object_or_404(User, id=user_id)
    now = timezone.now()
    
    statuses = Status.objects.filter(
        user=target_user,
        is_active=True,
        expires_at__gt=now
    ).order_by('created_at')
    
    if not statuses.exists():
        messages.error(request, 'No active statuses found.')
        return redirect('status_list')
    
    all_statuses = list(statuses)
    current_index = 0
    
    for status in all_statuses:
        view, created = StatusView.objects.get_or_create(
            status=status,
            user=request.user
        )
        if created:
            view.viewed = True
            view.save()
    
    context = {
        'target_user': target_user,
        'statuses': all_statuses,
        'current_index': current_index,
    }
    return render(request, 'chat_app/status_viewer.html', context)


@login_required
def status_delete_view(request, status_id):
    """Delete a status"""
    status = get_object_or_404(Status, id=status_id, user=request.user)
    status.delete()
    messages.success(request, 'Status deleted.')
    return redirect('status_list')


@login_required
def status_reply_view(request, status_id):
    """Reply to a status"""
    if request.method == 'POST':
        status = get_object_or_404(Status, id=status_id)
        reply_content = request.POST.get('reply', '').strip()
        
        if reply_content:
            view, created = StatusView.objects.get_or_create(
                status=status,
                user=request.user
            )
            view.replied = True
            view.reply_content = reply_content
            view.save()
            
            chat = Chat.objects.filter(
                participants=request.user
            ).filter(participants=status.user).first()
            
            if not chat:
                chat = Chat.objects.create(type='private')
                chat.participants.add(request.user, status.user)
            
            Message.objects.create(
                chat=chat,
                sender=request.user,
                content=f"Replied to {status.user.username}'s status: {reply_content}"
            )
            
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def my_status_viewers_view(request):
    """See who viewed your status"""
    from django.utils import timezone
    
    now = timezone.now()
    my_statuses = Status.objects.filter(user=request.user, is_active=True, expires_at__gt=now)
    
    viewers_data = []
    for status in my_statuses:
        views = StatusView.objects.filter(status=status).select_related('user')
        for view in views:
            viewers_data.append({
                'status': status,
                'user': view.user,
                'viewed_at': view.viewed_at,
                'replied': view.replied,
                'reply_content': view.reply_content
            })
    
    context = {
        'viewers_data': viewers_data,
    }
    return render(request, 'chat_app/my_status_viewers.html', context)


@login_required
def mark_messages_seen(request, chat_id):
    """Mark all messages in a chat as seen"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            chat = Chat.objects.get(id=chat_id, participants=request.user)
            
            # Get all unread messages from the other participant
            other_user = chat.get_other_participant(request.user)
            if other_user:
                # Mark messages as seen
                updated_count = Message.objects.filter(
                    chat=chat,
                    sender=other_user,
                    status__in=['sent', 'delivered']
                ).update(status='seen')
                
                return JsonResponse({
                    'status': 'success',
                    'updated_count': updated_count
                })
        except Chat.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Chat not found'}, status=404)
    
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def get_message_status(request, chat_id):
    """Get the status of all messages in a chat"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            chat = Chat.objects.get(id=chat_id, participants=request.user)
            messages = chat.messages.filter(is_deleted=False).order_by('created_at')
            
            message_statuses = []
            for msg in messages:
                message_statuses.append({
                    'id': msg.id,
                    'status': msg.status,
                    'sender_id': msg.sender_id
                })
            
            return JsonResponse({
                'status': 'success',
                'messages': message_statuses
            })
        except Chat.DoesNotExist:
            return JsonResponse({'status': 'error'}, status=404)
    
    return JsonResponse({'status': 'error'}, status=400)
