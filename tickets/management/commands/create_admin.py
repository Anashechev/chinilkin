from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user if it does not exist'

    def handle(self, *args, **options):
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123456')

        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(self.style.SUCCESS(f'Admin user "{admin_username}" already exists'))
            return

        User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            role='admin'
        )
        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user "{admin_username}"'))
