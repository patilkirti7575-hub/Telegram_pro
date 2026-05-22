from django.core.management.base import BaseCommand
from django.utils import timezone
from chat_app.models import User, Chat, Message
from datetime import timedelta


class Command(BaseCommand):
    help = 'Create dummy data for demo'

    def handle(self, *args, **options):
        self.stdout.write('Creating dummy data...')
        
        users_data = [
            {'username': 'john', 'email': 'john@example.com', 'password': 'pass123'},
            {'username': 'emma', 'email': 'emma@example.com', 'password': 'pass123'},
        ]
        
        users = {}
        for data in users_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={'email': data['email']}
            )
            if created:
                user.set_password(data['password'])
                user.is_online = True
                user.save()
                self.stdout.write(f'  Created: {user.username}')
            users[data['username']] = user
        
        john = users['john']
        emma = users['emma']
        
        chat = Chat.objects.filter(participants=john).filter(participants=emma).first()
        if not chat:
            chat = Chat.objects.create(type='private')
            chat.participants.add(john, emma)
            self.stdout.write('  Created chat: john <-> emma')
        
        messages_data = [
            (john, 'Hey Emma! How are you today?'),
            (emma, 'Hi John! I am doing great, thanks!'),
            (john, 'Did you watch the game last night?'),
            (emma, 'Yes! It was amazing! That last minute goal was incredible!'),
            (john, 'Absolutely! I was on the edge of my seat the whole time'),
            (emma, 'We should go watch the next match together at the sports bar'),
            (john, 'That sounds perfect! Saturday afternoon?'),
            (emma, 'Deal! I will meet you at 3 PM'),
        ]
        
        for i, (sender, content) in enumerate(messages_data):
            msg, created = Message.objects.get_or_create(
                chat=chat,
                sender=sender,
                content=content,
                defaults={'created_at': timezone.now() - timedelta(hours=len(messages_data)-i)}
            )
        
        self.stdout.write(self.style.SUCCESS('\nDummy data created!'))
        self.stdout.write(self.style.SUCCESS('\nTest Users:'))
        for data in users_data:
            self.stdout.write(f'  Username: {data["username"]} / Password: {data["password"]}')
