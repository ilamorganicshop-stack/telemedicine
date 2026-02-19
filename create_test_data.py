from django.contrib.auth import get_user_model
from medical.models import Hospital, DoctorProfile, PatientProfile, Availability
from django.utils import timezone
from datetime import datetime, timedelta

User = get_user_model()

# Create superuser
try:
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@telemedicine.com',
        password='admin123',
        first_name='Admin',
        last_name='User',
        role='admin'
    )
    print("Admin user created successfully")
except:
    print("Admin user already exists")

# Create hospitals
hospital1, created = Hospital.objects.get_or_create(
    name='City General Hospital',
    defaults={
        'address': '123 Main St, New York, NY 10001',
        'phone': '(212) 555-0101',
        'email': 'info@citygeneral.com',
        'website': 'https://www.citygeneral.com'
    }
)

hospital2, created = Hospital.objects.get_or_create(
    name='St. Mary Medical Center',
    defaults={
        'address': '456 Oak Ave, Los Angeles, CA 90001',
        'phone': '(213) 555-0202',
        'email': 'contact@stmary.com',
        'website': 'https://www.stmary.com'
    }
)

print("Hospitals created")

# Create doctors
try:
    doctor1 = User.objects.create_user(
        username='drsmith',
        email='smith@citygeneral.com',
        password='doctor123',
        first_name='John',
        last_name='Smith',
        role='doctor',
        phone='(212) 555-0102'
    )
    
    doctor_profile1 = DoctorProfile.objects.create(
        user=doctor1,
        hospital=hospital1,
        license_number='MD123456',
        specialization='Cardiology',
        experience_years=10,
        consultation_fee=250.00,
        bio='Experienced cardiologist with expertise in heart disease prevention and treatment.',
        education='Harvard Medical School, Residency at Johns Hopkins'
    )
    print("Doctor 1 created")
except:
    print("Doctor 1 already exists")

try:
    doctor2 = User.objects.create_user(
        username='drjones',
        email='jones@stmary.com',
        password='doctor123',
        first_name='Sarah',
        last_name='Jones',
        role='doctor',
        phone='(213) 555-0203'
    )
    
    doctor_profile2 = DoctorProfile.objects.create(
        user=doctor2,
        hospital=hospital2,
        license_number='MD789012',
        specialization='Pediatrics',
        experience_years=8,
        consultation_fee=200.00,
        bio='Dedicated pediatrician focused on child health and development.',
        education='Stanford Medical School, Residency at Children\'s Hospital'
    )
    print("Doctor 2 created")
except:
    print("Doctor 2 already exists")

# Create patients
try:
    patient1 = User.objects.create_user(
        username='johndoe',
        email='john.doe@email.com',
        password='patient123',
        first_name='John',
        last_name='Doe',
        role='patient',
        phone='(212) 555-0104',
        date_of_birth='1985-06-15'
    )
    
    patient_profile1 = PatientProfile.objects.create(
        user=patient1,
        hospital=hospital1,
        medical_history='Generally healthy, occasional hypertension.',
        allergies='Penicillin',
        emergency_contact_name='Jane Doe',
        emergency_contact_phone='(212) 555-0105',
        blood_type='O+'
    )
    print("Patient 1 created")
except:
    print("Patient 1 already exists")

try:
    patient2 = User.objects.create_user(
        username='janedoe',
        email='jane.doe@email.com',
        password='patient123',
        first_name='Jane',
        last_name='Doe',
        role='patient',
        phone='(213) 555-0204',
        date_of_birth='1990-03-22'
    )
    
    patient_profile2 = PatientProfile.objects.create(
        user=patient2,
        hospital=hospital2,
        medical_history='No major health issues.',
        allergies='None known',
        emergency_contact_name='John Doe',
        emergency_contact_phone='(213) 555-0205',
        blood_type='A+'
    )
    print("Patient 2 created")
except:
    print("Patient 2 already exists")

# Create doctor availability
doctors = User.objects.filter(role='doctor')
days_of_week = [0, 1, 2, 3, 4]  # Monday to Friday

for doctor in doctors:
    for day in days_of_week:
        Availability.objects.get_or_create(
            doctor=doctor,
            day_of_week=day,
            defaults={
                'start_time': datetime.strptime('09:00', '%H:%M').time(),
                'end_time': datetime.strptime('17:00', '%H:%M').time(),
                'is_available': True
            }
        )

print("Doctor availability created")
print("\nTest data creation complete!")
print("\nLogin credentials:")
print("Admin: username=admin, password=admin123")
print("Doctor 1: username=drsmith, password=doctor123")
print("Patient 1: username=johndoe, password=patient123")