import os
import urllib.parse

password = '301197997Mom@'
encoded_password = urllib.parse.quote_plus(password)
os.environ['DATABASE_URL'] = f'postgresql://postgres.slbzulmnmdncvkvdgbyy:{encoded_password}@aws-1-ap-south-1.pooler.supabase.com:5432/postgres'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telemedicine.settings')

import django
django.setup()

from django.core.management import call_command

print("Testing connection...")
from django.db import connection
connection.ensure_connection()
print("[OK] Connection successful!")

print("\nRunning migrations...")
call_command('migrate')

print("\nLoading data...")
call_command('loaddata', 'data_backup.json')

print("\n[OK] Migration complete!")
