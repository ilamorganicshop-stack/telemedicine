import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telemedicine.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

# Test data
test_cases = [
    ('doctor1@gmail.com', '123'),
    ('smith@citygeneral.com', 'doctor123'),
    ('admin@gmail.com', 'admin123'),
]

print("=" * 60)
print("LOGIN TEST SIMULATION")
print("=" * 60)

for email, password in test_cases:
    print(f"\n--- Testing: {email} ---")
    
    # Step 1: Find user by email
    user = User.objects.filter(email__iexact=email).first()
    print(f"1. User lookup: {user}")
    
    if user:
        print(f"2. Username: {user.username}")
        print(f"3. Email in DB: {user.email}")
        print(f"4. Has usable password: {user.has_usable_password()}")
        print(f"5. Check password '{password}': {user.check_password(password)}")
        
        # Step 2: Authenticate
        auth_result = authenticate(username=user.username, password=password)
        print(f"6. Authenticate result: {auth_result}")
        
        if auth_result:
            print("[SUCCESS] LOGIN WOULD SUCCEED")
        else:
            print("[FAIL] LOGIN WOULD FAIL - Password incorrect")
    else:
        print("[FAIL] LOGIN WOULD FAIL - User not found")

print("\n" + "=" * 60)
