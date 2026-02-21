from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
import requests
import json
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
                
                # Check if user is a patient and payment status
                if authenticated_user.role == 'patient':
                    try:
                        patient_profile = authenticated_user.patient_profile
                        if not patient_profile.payment_status:
                            # Patient hasn't paid, redirect to payment page
                            messages.info(request, 'Please complete your registration payment to access the dashboard.')
                            return redirect('accounts:khalti_payment')
                    except PatientProfile.DoesNotExist:
                        # No profile exists, redirect to payment
                        messages.info(request, 'Please complete your registration payment to access the dashboard.')
                        return redirect('accounts:khalti_payment')
                
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
    
    # Check if patient needs to pay
    if user.role == 'patient':
        try:
            patient_profile = user.patient_profile
            if not patient_profile.payment_status:
                messages.info(request, 'Please complete your registration payment to access the dashboard.')
                return redirect('accounts:khalti_payment')
        except PatientProfile.DoesNotExist:
            messages.info(request, 'Please complete your registration payment to access the dashboard.')
            return redirect('accounts:khalti_payment')
    
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
            
            # Get pending appointment requests
            pending_appointments = Appointment.objects.filter(
                doctor=user,
                status__in=['requested', 'pending_approval']
            ).order_by('appointment_date')
            
            total_patients = Appointment.objects.filter(
                doctor=user,
                status='completed'
            ).values('patient').distinct().count()
            
            context.update({
                'doctor_profile': doctor_profile,
                'today_appointments': today_appointments,
                'today_appointments_count': today_appointments.count(),
                'pending_appointments': pending_appointments,
                'pending_appointments_count': pending_appointments.count(),
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
            appointment.requested_by = request.user
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
        requested_by__isnull=False
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


# Khalti Payment Views

@login_required
def khalti_payment(request):
    """Initiate Khalti ePayment and redirect to payment page"""
    user = request.user
    
    if not user.is_patient:
        return redirect('accounts:dashboard')
    
    try:
        patient_profile = user.patient_profile
        if patient_profile.payment_status:
            return redirect('accounts:dashboard')
        
        # Check if already tried payment initiation (prevent redirect loop)
        if request.session.get('payment_init_attempted'):
            # Clear flag and show error page
            del request.session['payment_init_attempted']
            messages.error(request, 'Payment initiation failed. Please contact support.')
            return render(request, 'accounts/payment_error.html', {'user': user})
        
        hospital = patient_profile.hospital
        appointment_fee = hospital.appointment_fee if hospital else 1000.00
        amount_in_paisa = int(appointment_fee * 100)
        
        # Mark that we're attempting payment
        request.session['payment_init_attempted'] = True
        
        # Initiate payment with Khalti ePayment API
        url = settings.KHALTI_GATEWAY_URL
        payload = {
            "return_url": request.build_absolute_uri(reverse('accounts:khalti_verify')),
            "website_url": request.build_absolute_uri('/'),
            "amount": amount_in_paisa,
            "purchase_order_id": f"PATIENT-{user.id}-{int(timezone.now().timestamp())}",
            "purchase_order_name": "Appointment Fee",
            "customer_info": {
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "phone": user.phone or "9800000000"
            }
        }
        
        headers = {
            'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('payment_url'):
            # Clear attempt flag on success
            del request.session['payment_init_attempted']
            # Store pidx in session for verification
            request.session['khalti_pidx'] = response_data.get('pidx')
            # Redirect to Khalti payment page
            return redirect(response_data['payment_url'])
        else:
            # Clear attempt flag
            del request.session['payment_init_attempted']
            error_msg = response_data.get('detail') or response_data.get('error_message') or 'Unknown error'
            messages.error(request, f"Payment initiation failed: {error_msg}")
            return render(request, 'accounts/payment_error.html', {
                'user': user,
                'error': error_msg,
                'response': response_data
            })
            
    except PatientProfile.DoesNotExist:
        messages.error(request, 'Patient profile not found. Please contact support.')
        return redirect('accounts:login')
    except Exception as e:
        # Clear attempt flag
        if 'payment_init_attempted' in request.session:
            del request.session['payment_init_attempted']
        messages.error(request, f'Payment error: {str(e)}')
        return render(request, 'accounts/payment_error.html', {
            'user': user,
            'error': str(e)
        })


@login_required
def khalti_verify(request):
    """Verify Khalti ePayment callback"""
    user = request.user
    
    if not user.is_patient:
        messages.error(request, 'Invalid access')
        return redirect('accounts:dashboard')
    
    # Get pidx from query params (Khalti callback)
    pidx = request.GET.get('pidx')
    
    if not pidx:
        messages.error(request, 'Payment verification failed: No transaction ID')
        return redirect('accounts:khalti_payment')
    
    try:
        patient_profile = user.patient_profile
        
        if patient_profile.payment_status:
            messages.info(request, 'Payment already completed')
            return redirect('accounts:dashboard')
        
        # Verify payment with Khalti API
        url = settings.KHALTI_VERIFY_URL
        headers = {
            'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        payload = {"pidx": pidx}
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('status') == 'Completed':
            # Payment successful
            patient_profile.payment_status = True
            patient_profile.khalti_transaction_id = pidx
            patient_profile.save()
            
            messages.success(request, 'Payment completed successfully!')
            return redirect('accounts:payment_success')
        else:
            messages.error(request, f"Payment verification failed: {response_data.get('status', 'Unknown')}")
            return redirect('accounts:khalti_payment')
            
    except PatientProfile.DoesNotExist:
        messages.error(request, 'Patient profile not found')
        return redirect('accounts:login')
    except Exception as e:
        messages.error(request, f'Verification error: {str(e)}')
        return redirect('accounts:khalti_payment')


@login_required
def payment_success(request):
    """Display payment success page and redirect to dashboard"""
    user = request.user
    
    if not user.is_patient:
        return redirect('accounts:dashboard')
    
    try:
        patient_profile = user.patient_profile
        if not patient_profile.payment_status:
            messages.error(request, 'Payment not completed.')
            return redirect('accounts:khalti_payment')
    except PatientProfile.DoesNotExist:
        return redirect('accounts:login')
    
    messages.success(request, 'Payment completed successfully! Welcome to your dashboard.')
    return render(request, 'accounts/payment_success.html', {
        'user': user,
        'transaction_id': patient_profile.khalti_transaction_id
    })


# Hospital Admin CRUD Views

@login_required
@user_passes_test(is_hospital_admin)
def edit_patient(request, pk):
    hospital = request.user.hospital
    patient = get_object_or_404(User, pk=pk, role='patient', hospital=hospital)
    
    if request.method == 'POST':
        from .admin_forms import PatientEditForm
        form = PatientEditForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient "{patient.email}" updated successfully!')
            return redirect('accounts:manage_patients')
    else:
        from .admin_forms import PatientEditForm
        form = PatientEditForm(instance=patient)
        form.fields['hospital'].queryset = Hospital.objects.filter(id=hospital.id)
        form.fields['hospital'].widget.attrs['disabled'] = True
    
    return render(request, 'accounts/edit_patient.html', {'form': form, 'patient': patient})


@login_required
@user_passes_test(is_hospital_admin)
def delete_patient(request, pk):
    hospital = request.user.hospital
    patient = get_object_or_404(User, pk=pk, role='patient', hospital=hospital)
    
    if request.method == 'POST':
        email = patient.email
        patient.delete()
        messages.success(request, f'Patient "{email}" deleted successfully!')
        return redirect('accounts:manage_patients')
    
    return render(request, 'accounts/delete_confirm.html', {
        'object': patient,
        'object_type': 'Patient',
        'cancel_url': 'accounts:manage_patients'
    })


@login_required
@user_passes_test(is_hospital_admin)
def edit_doctor(request, pk):
    hospital = request.user.hospital
    doctor = get_object_or_404(User, pk=pk, role='doctor', hospital=hospital)
    
    if request.method == 'POST':
        from .admin_forms import DoctorEditForm
        form = DoctorEditForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Doctor "{doctor.email}" updated successfully!')
            return redirect('accounts:manage_doctors')
    else:
        from .admin_forms import DoctorEditForm
        form = DoctorEditForm(instance=doctor)
        form.fields['hospital'].queryset = Hospital.objects.filter(id=hospital.id)
        form.fields['hospital'].widget.attrs['disabled'] = True
    
    return render(request, 'accounts/edit_doctor.html', {'form': form, 'doctor': doctor})


@login_required
@user_passes_test(is_hospital_admin)
def delete_doctor(request, pk):
    hospital = request.user.hospital
    doctor = get_object_or_404(User, pk=pk, role='doctor', hospital=hospital)
    
    if request.method == 'POST':
        email = doctor.email
        doctor.delete()
        messages.success(request, f'Doctor "{email}" deleted successfully!')
        return redirect('accounts:manage_doctors')
    
    return render(request, 'accounts/delete_confirm.html', {
        'object': doctor,
        'object_type': 'Doctor',
        'cancel_url': 'accounts:manage_doctors'
    })


# Super Admin CRUD Views

@login_required
@user_passes_test(is_super_admin)
def super_admin_edit_patient(request, pk):
    patient = get_object_or_404(User, pk=pk, role='patient')
    
    if request.method == 'POST':
        from .admin_forms import PatientEditForm
        form = PatientEditForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient "{patient.email}" updated successfully!')
            return redirect('accounts:super_admin_manage_patients')
    else:
        from .admin_forms import PatientEditForm
        form = PatientEditForm(instance=patient)
    
    return render(request, 'accounts/edit_patient.html', {'form': form, 'patient': patient})


@login_required
@user_passes_test(is_super_admin)
def super_admin_delete_patient(request, pk):
    patient = get_object_or_404(User, pk=pk, role='patient')
    
    if request.method == 'POST':
        email = patient.email
        patient.delete()
        messages.success(request, f'Patient "{email}" deleted successfully!')
        return redirect('accounts:super_admin_manage_patients')
    
    return render(request, 'accounts/delete_confirm.html', {
        'object': patient,
        'object_type': 'Patient',
        'cancel_url': 'accounts:super_admin_manage_patients'
    })


@login_required
@user_passes_test(is_super_admin)
def super_admin_edit_doctor(request, pk):
    doctor = get_object_or_404(User, pk=pk, role='doctor')
    
    if request.method == 'POST':
        from .admin_forms import DoctorEditForm
        form = DoctorEditForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Doctor "{doctor.email}" updated successfully!')
            return redirect('accounts:super_admin_manage_doctors')
    else:
        from .admin_forms import DoctorEditForm
        form = DoctorEditForm(instance=doctor)
    
    return render(request, 'accounts/edit_doctor.html', {'form': form, 'doctor': doctor})


@login_required
@user_passes_test(is_super_admin)
def super_admin_delete_doctor(request, pk):
    doctor = get_object_or_404(User, pk=pk, role='doctor')
    
    if request.method == 'POST':
        email = doctor.email
        doctor.delete()
        messages.success(request, f'Doctor "{email}" deleted successfully!')
        return redirect('accounts:super_admin_manage_doctors')
    
    return render(request, 'accounts/delete_confirm.html', {
        'object': doctor,
        'object_type': 'Doctor',
        'cancel_url': 'accounts:super_admin_manage_doctors'
    })


@login_required
@user_passes_test(is_super_admin)
def super_admin_edit_admin(request, pk):
    admin = get_object_or_404(User, pk=pk, role='admin')
    
    if request.method == 'POST':
        from .admin_forms import HospitalAdminCreationForm
        form = HospitalAdminCreationForm(request.POST, instance=admin)
        # Make passwords optional for edit
        form.fields['password1'].required = False
        form.fields['password2'].required = False
        if form.is_valid():
            form.save()
            messages.success(request, f'Admin "{admin.email}" updated successfully!')
            return redirect('accounts:super_admin_manage_admins')
    else:
        from .admin_forms import HospitalAdminCreationForm
        form = HospitalAdminCreationForm(instance=admin)
        form.fields['password1'].required = False
        form.fields['password2'].required = False
    
    return render(request, 'accounts/edit_admin.html', {'form': form, 'admin': admin})


@login_required
@user_passes_test(is_super_admin)
def super_admin_delete_admin(request, pk):
    admin = get_object_or_404(User, pk=pk, role='admin')
    
    if request.method == 'POST':
        email = admin.email
        admin.delete()
        messages.success(request, f'Admin "{email}" deleted successfully!')
        return redirect('accounts:super_admin_manage_admins')
    
    return render(request, 'accounts/delete_confirm.html', {
        'object': admin,
        'object_type': 'Admin',
        'cancel_url': 'accounts:super_admin_manage_admins'
    })


@login_required
@user_passes_test(is_super_admin)
def edit_hospital(request, pk):
    hospital = get_object_or_404(Hospital, pk=pk)
    
    if request.method == 'POST':
        form = HospitalForm(request.POST, instance=hospital)
        if form.is_valid():
            form.save()
            messages.success(request, f'Hospital "{hospital.name}" updated successfully!')
            return redirect('accounts:manage_hospitals')
    else:
        form = HospitalForm(instance=hospital)
    
    return render(request, 'accounts/edit_hospital.html', {'form': form, 'hospital': hospital})


@login_required
@user_passes_test(is_super_admin)
def delete_hospital(request, pk):
    hospital = get_object_or_404(Hospital, pk=pk)
    
    if request.method == 'POST':
        name = hospital.name
        hospital.delete()
        messages.success(request, f'Hospital "{name}" deleted successfully!')
        return redirect('accounts:manage_hospitals')
    
    return render(request, 'accounts/delete_confirm.html', {
        'object': hospital,
        'object_type': 'Hospital',
        'cancel_url': 'accounts:manage_hospitals'
    })
