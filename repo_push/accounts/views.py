from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.utils import timezone
from .forms import UserCreationForm
from .admin_forms import HospitalForm, HospitalAdminCreationForm, DoctorCreationForm, PatientCreationForm, AdminAppointmentBookingForm, AppointmentApprovalForm
from .models import User
from medical.models import Hospital, DoctorProfile, PatientProfile, Appointment


def login_view(request):
    if request.method == 'POST':
        print(f"DEBUG: POST data: {request.POST}")
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password')
        
        print(f"DEBUG: Email received: [{email}]")
        print(f"DEBUG: Password received: [{password}]")
        print(f"DEBUG: Password length: {len(password) if password else 0}")

        master_email = 'admin@gmail.com'
        master_password = 'admin123'

        if email.lower() == master_email and password == master_password:
            user, created = User.objects.get_or_create(
                email=master_email,
                defaults={
                    'username': master_email,
                    'role': 'super_admin',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if not created:
                user.role = 'super_admin'
                user.is_staff = True
                user.is_superuser = True
            # Always keep the master account on the requested password.
            user.set_password(master_password)
            user.save()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('accounts:dashboard')

        user = User.objects.filter(email__iexact=email).first()
        print(f"DEBUG: User found: {user}")
        if user is None:
            messages.error(request, 'Invalid username or password. Please try again.')
        else:
            print(f"DEBUG: Authenticating with username: [{user.username}] and password: [{password}]")
            authenticated_user = authenticate(request, username=user.username, password=password)
            print(f"DEBUG: Authentication result: {authenticated_user}")
            if authenticated_user is not None:
                login(request, authenticated_user)
                messages.success(request, f'Welcome back, {authenticated_user.username}!')
                return redirect('accounts:dashboard')
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


class SignUpView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self, 'Account created successfully! Please log in.')
        return response


@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}
    
    if user.is_super_admin:
        return redirect('accounts:super_admin_dashboard')
    elif user.is_admin_user:
        return redirect('accounts:hospital_admin_dashboard')
        
    elif user.is_doctor:
        # Doctor dashboard data
        try:
            doctor_profile = user.doctor_profile
        except DoctorProfile.DoesNotExist:
            doctor_profile = None
        
        # Only continue if doctor has both user role and profile
        if doctor_profile and user.hospital:
            today = timezone.now().date()
            today_appointments = Appointment.objects.filter(
                doctor=user,
                appointment_date__date=today,
                status__in=['scheduled', 'confirmed']
            ).order_by('appointment_date')
            
            total_patients = Appointment.objects.filter(
                doctor=user,
                status='completed'
            ).values('patient').distinct().count()
            
            context.update({
                'doctor_profile': doctor_profile,
                'today_appointments': today_appointments,
                'today_appointments_count': today_appointments.count(),
                'total_patients': total_patients,
            })
            template_name = 'accounts/doctor_dashboard.html'
            return render(request, template_name, context)
        else:
            # Doctor doesn't have proper profile/hospital assignment
            return redirect('accounts:login')
            
        today = timezone.now().date()
        today_appointments = Appointment.objects.filter(
            doctor=user,
            appointment_date__date=today,
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date')
        
        total_patients = Appointment.objects.filter(
            doctor=user,
            status='completed'
        ).values('patient').distinct().count()
        
        doctor_context = {
            'doctor_profile': doctor_profile,
            'today_appointments': today_appointments,
            'today_appointments_count': today_appointments.count(),
            'total_patients': total_patients,
        }
        return render(request, 'accounts/doctor_dashboard.html', doctor_context)
        
    else:  # patient
        try:
            patient_profile = user.patient_profile
        except PatientProfile.DoesNotExist:
            patient_profile = None
            
        upcoming_appointments = Appointment.objects.filter(
            patient=user,
            appointment_date__gte=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date')
        
        completed_appointments = Appointment.objects.filter(
            patient=user,
            status='completed'
        ).count()
        
        # Get unique doctors the patient has seen
        doctor_count = Appointment.objects.filter(
            patient=user,
            status='completed'
        ).values('doctor').distinct().count()
        
        patient_context = {
            'patient_profile': patient_profile,
            'upcoming_appointments': upcoming_appointments,
            'upcoming_appointments_count': upcoming_appointments.count(),
            'completed_appointments': completed_appointments,
            'doctor_count': doctor_count,
        }
        return render(request, 'accounts/patient_dashboard.html', patient_context)


# Helper functions
def is_super_admin(user):
    return user.is_authenticated and user.is_super_admin


def is_hospital_admin(user):
    return user.is_authenticated and user.is_admin_user


# Super Admin Views
@login_required
@user_passes_test(is_super_admin)
def super_admin_dashboard(request):
    total_hospitals = Hospital.objects.count()
    total_admins = User.objects.filter(role='admin').count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_patients = User.objects.filter(role='patient').count()
    recent_hospitals = Hospital.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-created_at')[:5]
    
    context = {
        'total_hospitals': total_hospitals,
        'total_admins': total_admins,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'recent_hospitals': recent_hospitals,
        'recent_users': recent_users,
    }
    return render(request, 'accounts/super_admin_dashboard.html', context)


@login_required
@user_passes_test(is_super_admin)
def create_hospital(request):
    if request.method == 'POST':
        form = HospitalForm(request.POST)
        if form.is_valid():
            hospital = form.save()
            messages.success(request, f'Hospital "{hospital.name}" created successfully!')
            return redirect('accounts:super_admin_dashboard')
    else:
        form = HospitalForm()
    
    return render(request, 'accounts/create_hospital.html', {'form': form})


@login_required
@user_passes_test(is_super_admin)
def manage_hospitals(request):
    hospitals = Hospital.objects.all().order_by('-created_at')
    return render(request, 'accounts/manage_hospitals.html', {'hospitals': hospitals})


@login_required
@user_passes_test(is_super_admin)
def create_hospital_admin(request):
    if request.method == 'POST':
        form = HospitalAdminCreationForm(request.POST)
        if form.is_valid():
            admin = form.save()
            messages.success(request, f'Hospital admin "{admin.username}" created successfully!')
            return redirect('accounts:super_admin_dashboard')
    else:
        form = HospitalAdminCreationForm()
    
    return render(request, 'accounts/create_hospital_admin.html', {'form': form})


# Hospital Admin Views
@login_required
@user_passes_test(is_hospital_admin)
def hospital_admin_dashboard(request):
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'You are not assigned to any hospital. Please contact the super admin.')
        return redirect('accounts:login')
    
    doctors = User.objects.filter(role='doctor', hospital=hospital)
    patients = User.objects.filter(role='patient', hospital=hospital)
    
    context = {
        'hospital': hospital,
        'doctors': doctors,
        'patients': patients,
        'doctors_count': doctors.count(),
        'patients_count': patients.count(),
    }
    return render(request, 'accounts/hospital_admin_dashboard.html', context)


@login_required
@user_passes_test(is_hospital_admin)
def create_doctor(request):
    hospital = request.user.hospital
    if request.method == 'POST':
        form = DoctorCreationForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'Doctor "{doctor.username}" created successfully!')
            return redirect('accounts:hospital_admin_dashboard')
    else:
        form = DoctorCreationForm(initial={'hospital': hospital})
        # Filter hospital choice to current hospital only
        form.fields['hospital'].queryset = Hospital.objects.filter(id=hospital.id)
        form.fields['hospital'].widget.attrs['disabled'] = True
    
    return render(request, 'accounts/create_doctor.html', {
        'form': form,
        'hospital': hospital,
        'cancel_url': 'accounts:hospital_admin_dashboard',
    })


@login_required
@user_passes_test(is_hospital_admin)
def create_patient(request):
    hospital = request.user.hospital
    if request.method == 'POST':
        form = PatientCreationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient "{patient.username}" created successfully!')
            return redirect('accounts:hospital_admin_dashboard')
    else:
        form = PatientCreationForm(initial={'hospital': hospital})
        # Filter hospital choice to current hospital only
        form.fields['hospital'].queryset = Hospital.objects.filter(id=hospital.id)
        form.fields['hospital'].widget.attrs['disabled'] = True
    
    return render(request, 'accounts/create_patient.html', {
        'form': form,
        'hospital': hospital,
        'cancel_url': 'accounts:hospital_admin_dashboard',
    })


@login_required
@user_passes_test(is_hospital_admin)
def manage_doctors(request):
    hospital = request.user.hospital
    doctors = User.objects.filter(role='doctor', hospital=hospital).order_by('-created_at')
    return render(request, 'accounts/manage_doctors.html', {
        'doctors': doctors,
        'scope_label': hospital.name if hospital else 'your hospital',
        'show_hospital': False,
        'create_url_name': 'accounts:create_doctor',
    })


@login_required
@user_passes_test(is_hospital_admin)
def manage_patients(request):
    hospital = request.user.hospital
    patients = User.objects.filter(role='patient', hospital=hospital).order_by('-created_at')
    return render(request, 'accounts/manage_patients.html', {
        'patients': patients,
        'scope_label': hospital.name if hospital else 'your hospital',
        'show_hospital': False,
        'create_url_name': 'accounts:create_patient',
    })


# Super Admin Management Views
@login_required
@user_passes_test(is_super_admin)
def super_admin_manage_doctors(request):
    doctors = User.objects.filter(role='doctor').select_related('hospital').order_by('-created_at')
    return render(request, 'accounts/super_admin_manage_doctors.html', {
        'doctors': doctors,
        'scope_label': 'all hospitals',
        'show_hospital': True,
        'create_url_name': 'accounts:super_admin_create_doctor',
    })


@login_required
@user_passes_test(is_super_admin)
def super_admin_manage_patients(request):
    patients = User.objects.filter(role='patient').select_related('hospital').order_by('-created_at')
    return render(request, 'accounts/super_admin_manage_patients.html', {
        'patients': patients,
        'scope_label': 'all hospitals',
        'show_hospital': True,
        'create_url_name': 'accounts:super_admin_create_patient',
    })


@login_required
@user_passes_test(is_super_admin)
def super_admin_manage_admins(request):
    admins = User.objects.filter(role='admin').select_related('hospital').order_by('-created_at')
    return render(request, 'accounts/manage_admins.html', {
        'admins': admins,
    })


@login_required
@user_passes_test(is_super_admin)
def super_admin_create_doctor(request):
    if request.method == 'POST':
        form = DoctorCreationForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'Doctor "{doctor.username}" created successfully!')
            return redirect('accounts:super_admin_manage_doctors')
    else:
        form = DoctorCreationForm()

    return render(request, 'accounts/super_admin_create_doctor.html', {
        'form': form,
        'hospital': None,
        'cancel_url': 'accounts:super_admin_manage_doctors',
    })


@login_required
@user_passes_test(is_super_admin)
def super_admin_create_patient(request):
    if request.method == 'POST':
        form = PatientCreationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient "{patient.username}" created successfully!')
            return redirect('accounts:super_admin_manage_patients')
    else:
        form = PatientCreationForm()

    return render(request, 'accounts/super_admin_create_patient.html', {
        'form': form,
        'hospital': None,
        'cancel_url': 'accounts:super_admin_manage_patients',
    })


# Hospital Admin Appointment Management Views
@login_required
@user_passes_test(is_hospital_admin)
def book_appointment(request):
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'You are not assigned to any hospital. Please contact to super admin.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = AdminAppointmentBookingForm(request.POST, hospital=hospital)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.requested_by_admin = request.user
            # Also track admin hospital for reference
            if request.user.hospital:
                appointment.hospital = request.user.hospital
            appointment.hospital = hospital
            appointment.status = 'requested'
            appointment.save()
            
            messages.success(request, f'Appointment requested for {appointment.patient.first_name} {appointment.patient.last_name} with Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}')
            return redirect('accounts:manage_appointments')
    else:
        form = AdminAppointmentBookingForm(hospital=hospital)
    
    return render(request, 'accounts/book_appointment.html', {'form': form})


@login_required
@user_passes_test(is_hospital_admin)
def manage_appointments(request):
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'You are not assigned to any hospital. Please contact to super admin.')
        return redirect('accounts:login')
    
    appointments = Appointment.objects.filter(
        hospital=hospital,
        requested_by_admin__isnull=False
    ).order_by('-created_at')
    
    return render(request, 'accounts/manage_appointments.html', {'appointments': appointments})


# Doctor Appointment Approval Views

def is_doctor(user):
    return user.is_authenticated and hasattr(user, 'role') and user.role == 'doctor'

@login_required
@user_passes_test(is_doctor)
def pending_appointments(request):
    """Show pending appointments for doctors"""
    appointments = Appointment.objects.filter(
        doctor=request.user,
        status__in=['requested', 'pending_approval']
    ).order_by('appointment_date')
    
    return render(request, 'accounts/pending_appointments.html', {'appointments': appointments})


@login_required
@user_passes_test(is_doctor)
def approve_reject_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    
    if appointment.status not in ['requested', 'pending_approval']:
        messages.error(request, 'This appointment cannot be processed.')
        return redirect('accounts:pending_appointments')
    
    if request.method == 'POST':
        form = AppointmentApprovalForm(request.POST)
        if form.is_valid():
            approval_status = form.cleaned_data['approval_status']
            
            if approval_status == 'approve':
                appointment.status = 'scheduled'
                messages.success(request, 'Appointment approved and scheduled successfully!')
                
            elif approval_status == 'modify':
                new_date = form.cleaned_data.get('new_date')
                new_time = form.cleaned_data.get('new_time')
                if new_date:
                    appointment.appointment_date = new_date
                if new_time:
                    # Combine date and time if both provided
                    from datetime import datetime, time as dt_time
                    if isinstance(new_time, str):
                        time_parts = new_time.split(':')
                        new_time = dt_time(int(time_parts[0]), int(time_parts[1]))
                    new_datetime = datetime.combine(new_date.date(), new_time)
                    appointment.appointment_date = new_datetime
                else:
                    appointment.appointment_date = new_date
                
                appointment.status = 'pending_approval'
                messages.info(request, 'Requested schedule change sent to admin.')
                
            elif approval_status == 'reject':
                appointment.status = 'rejected'
                appointment.rejection_reason = form.cleaned_data['rejection_reason']
                messages.error(request, f'Appointment rejected: {appointment.rejection_reason}')
            
            appointment.save()
            return redirect('accounts:pending_appointments')
    else:
        form = AppointmentApprovalForm()
    
    return render(request, 'accounts/approve_reject_appointment.html', {
        'appointment': appointment,
        'form': form
    })
