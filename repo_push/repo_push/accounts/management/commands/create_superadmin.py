from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from accounts.models import User


class Command(BaseCommand):
    help = 'Create hardcoded super admin user'

    def handle(self, *args, **options):
        username = 'superadmin'
        password = 'admin123'
        email = 'superadmin@telemedicine.com'
        first_name = 'Super'
        last_name = 'Admin'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING('Super admin user already exists.'))
            return
        
        super_admin = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=make_password(password),
            role='super_admin',
            is_staff=True,
            is_superuser=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created super admin: {username}/{password}')
        )