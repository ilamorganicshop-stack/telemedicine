import os
import sys

# Set the Supabase database URL
SUPABASE_PASSWORD = input("Enter Supabase password: ")
os.environ['DATABASE_URL'] = f'postgresql://postgres:{SUPABASE_PASSWORD}@db.slbzulmnmdncvkvdgbyy.supabase.co:5432/postgres'

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telemedicine.settings')
import django
django.setup()

from django.core.management import call_command

print("Running migrations on Supabase...")
call_command('migrate')

print("\nLoading data into Supabase...")
call_command('loaddata', 'data_backup.json')

print("\n✓ Migration complete!")
