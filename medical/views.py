import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Hospital, DoctorProfile, PatientProfile, Appointment, Availability, ChatMessage

User = get_user_model()


@login_required
def hospital_list(request):
    hospitals = Hospital.objects.all()
    return render(request, 'medical/hospital_list.html', {'hospitals': hospitals})


@login_required
def hospital_detail(request, hospital_id):
    hospital = get_object_or_404(Hospital, id=hospital_id)
    doctors = hospital.doctors.all()
    return render(request, 'medical/hospital_detail.html', {'hospital': hospital, 'doctors': doctors})


@login_required
def doctor_list(request):
    doctors = DoctorProfile.objects.select_related('user', 'hospital').all()
    return render(request, 'medical/doctor_list.html', {'doctors': doctors})


@login_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile.objects.select_related('user', 'hospital'), id=doctor_id)
    today = timezone.now().date()
    
    # Get doctor's availability for today
    day_of_week = today.weekday()
    try:
        availability = Availability.objects.get(doctor=doctor.user, day_of_week=day_of_week)
    except Availability.DoesNotExist:
        availability = None
    
    # Get upcoming appointments for this doctor
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor.user,
        appointment_date__gte=timezone.now(),
        status__in=['scheduled', 'confirmed']
    ).order_by('appointment_date')[:5]
    
    return render(request, 'medical/doctor_detail.html', {
        'doctor': doctor,
        'availability': availability,
        'upcoming_appointments': upcoming_appointments
    })


@login_required
def patient_list(request):
    if not request.user.is_doctor and not request.user.is_admin_user:
        messages.error(request, "You don't have permission to view patients.")
        return redirect('dashboard')
    
    patients = PatientProfile.objects.select_related('user', 'hospital').all()
    return render(request, 'medical/patient_list.html', {'patients': patients})


@login_required
def patient_detail(request, patient_id):
    if not request.user.is_doctor and not request.user.is_admin_user:
        messages.error(request, "You don't have permission to view patient details.")
        return redirect('dashboard')
    
    patient = get_object_or_404(PatientProfile.objects.select_related('user', 'hospital'), id=patient_id)
    
    # Get patient's appointment history
    appointments = Appointment.objects.filter(
        patient=patient.user
    ).select_related('doctor', 'hospital').order_by('-appointment_date')
    
    return render(request, 'medical/patient_detail.html', {
        'patient': patient,
        'appointments': appointments
    })


@login_required
def appointment_list(request):
    user = request.user
    
    if user.is_doctor:
        appointments = Appointment.objects.filter(
            doctor=user
        ).select_related('patient', 'hospital').order_by('-appointment_date')
    elif user.is_patient:
        appointments = Appointment.objects.filter(
            patient=user
        ).select_related('doctor', 'hospital').order_by('-appointment_date')
    else:  # admin
        appointments = Appointment.objects.select_related(
            'patient', 'doctor', 'hospital'
        ).order_by('-appointment_date')
    
    return render(request, 'medical/appointment_list.html', {'appointments': appointments})


@login_required
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor', 'hospital'),
        id=appointment_id
    )
    
    # Check permissions
    user = request.user
    if not (user.is_admin_user or user == appointment.patient or user == appointment.doctor):
        messages.error(request, "You don't have permission to view this appointment.")
        return redirect('dashboard')
    
    return render(request, 'medical/appointment_detail.html', {'appointment': appointment})


@login_required
def create_appointment(request):
    if not request.user.is_patient:
        messages.error(request, "Only patients can create appointments.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        hospital_id = request.POST.get('hospital')
        appointment_date = request.POST.get('appointment_date')
        symptoms = request.POST.get('symptoms', '')
        
        try:
            doctor = User.objects.get(id=doctor_id, role='doctor')
            hospital = Hospital.objects.get(id=hospital_id)
            
            # Parse appointment date
            from datetime import datetime
            appointment_datetime = datetime.strptime(appointment_date, '%Y-%m-%dT%H:%M')
            
            # Check for conflicts
            conflict = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_datetime,
                status__in=['scheduled', 'confirmed', 'in_progress']
            ).exists()
            
            if conflict:
                messages.error(request, "This time slot is already booked. Please choose another time.")
            else:
                appointment = Appointment.objects.create(
                    patient=request.user,
                    doctor=doctor,
                    hospital=hospital,
                    appointment_date=appointment_datetime,
                    symptoms=symptoms
                )
                messages.success(request, f"Appointment scheduled with Dr. {doctor.first_name} {doctor.last_name}!")
                return redirect('medical:appointment_detail', appointment_id=appointment.id)
                
        except (User.DoesNotExist, Hospital.DoesNotExist, ValueError) as e:
            messages.error(request, "Invalid selection. Please try again.")
    
    # Get available doctors and hospitals
    doctors = DoctorProfile.objects.select_related('user', 'hospital').filter(is_available=True)
    hospitals = Hospital.objects.all()
    
    return render(request, 'medical/create_appointment.html', {
        'doctors': doctors,
        'hospitals': hospitals
    })


@login_required
def update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Check permissions
    if not (user.is_admin_user or user == appointment.doctor):
        messages.error(request, "You don't have permission to update this appointment.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.updated_at = timezone.now()
            appointment.save()
            messages.success(request, f"Appointment status updated to {appointment.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")
    
    return redirect('medical:appointment_detail', appointment_id=appointment.id)


@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Check permissions (patients can cancel their own appointments)
    if not (user.is_admin_user or user == appointment.patient or user == appointment.doctor):
        messages.error(request, "You don't have permission to cancel this appointment.")
        return redirect('dashboard')
    
    # Only allow cancellation if appointment is not completed
    if appointment.status == 'completed':
        messages.error(request, "Cannot cancel completed appointments.")
        return redirect('medical:appointment_detail', appointment_id=appointment.id)
    
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.updated_at = timezone.now()
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")
    
    return redirect('medical:appointment_detail', appointment_id=appointment.id)


@login_required
def chat_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor', 'hospital'),
        id=appointment_id
    )
    
    # Check permissions
    user = request.user
    if not (user.is_admin_user or user == appointment.patient or user == appointment.doctor):
        messages.error(request, "You don't have permission to access this chat.")
        return redirect('dashboard')
    
    # Get chat messages
    chat_messages = ChatMessage.objects.filter(
        appointment=appointment
    ).select_related('sender').order_by('created_at')
    
    # Mark messages as read if user is not the sender
    if user == appointment.doctor:
        ChatMessage.objects.filter(
            appointment=appointment,
            sender=appointment.patient,
            is_read=False
        ).update(is_read=True)
    elif user == appointment.patient:
        ChatMessage.objects.filter(
            appointment=appointment,
            sender=appointment.doctor,
            is_read=False
        ).update(is_read=True)
    
    return render(request, 'medical/chat.html', {
        'appointment': appointment,
        'messages': chat_messages
    })


@login_required
def send_message(request, appointment_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Check permissions
    if not (user.is_admin_user or user == appointment.patient or user == appointment.doctor):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    message_text = request.POST.get('message', '').strip()
    if not message_text:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    
    # Create message
    message = ChatMessage.objects.create(
        appointment=appointment,
        sender=user,
        message=message_text
    )
    
    return JsonResponse({
        'success': True,
        'message_id': message.id,
        'message': message.message,
        'sender': f"{message.sender.first_name} {message.sender.last_name}",
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_self': message.sender == user
    })


# ==================== VIDEO CALL VIEWS ====================

@login_required
def video_call_view(request, appointment_id):
    """Main video call page for doctor or patient"""
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor', 'hospital'),
        id=appointment_id
    )
    
    user = request.user
    
    # Check permissions
    if not (user == appointment.patient or user == appointment.doctor):
        messages.error(request, "You don't have permission to join this video call.")
        return redirect('dashboard')
    
    # Determine user type
    user_type = 'doctor' if user == appointment.doctor else 'patient'
    
    # Validate token
    token = request.GET.get('token')
    valid_token = False
    
    if user_type == 'doctor' and token == appointment.doctor_token:
        valid_token = appointment.is_token_valid('doctor')
    elif user_type == 'patient' and token == appointment.patient_token:
        valid_token = appointment.is_token_valid('patient')
    
    if not valid_token:
        messages.error(request, "Invalid or expired access token.")
        return redirect('medical:chat', appointment_id=appointment.id)
    
    # If doctor is joining, mark call as in progress
    if user_type == 'doctor' and appointment.video_call_status == 'waiting':
        appointment.start_video_call()
    
    # Get WebRTC configuration
    webrtc_config = {
        'stun_servers': settings.WEBRTC_STUN_SERVERS,
        'turn_servers': settings.WEBRTC_TURN_SERVERS,
    }
    
    return render(request, 'medical/video_call.html', {
        'appointment': appointment,
        'user_type': user_type,
        'room_id': appointment.video_call_room_id,
        'webrtc_config': json.dumps(webrtc_config),
    })


@login_required
def start_video_call(request, appointment_id):
    """Doctor initiates video call"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Only doctor can start the call
    if user != appointment.doctor:
        messages.error(request, "Only the doctor can start the video call.")
        return redirect('medical:chat', appointment_id=appointment.id)
    
    # Generate room ID and tokens if not already created
    if not appointment.video_call_room_id:
        appointment.generate_room_id()
    
    if not appointment.doctor_token or not appointment.patient_token:
        appointment.generate_tokens()
        appointment.save()
    
    # Set status to waiting (patient needs to join)
    appointment.video_call_status = 'waiting'
    appointment.save()
    
    # Redirect doctor to video call room
    return redirect(f'/medical/appointments/{appointment.id}/video-call/?token={appointment.doctor_token}')


@login_required
def join_video_call(request, appointment_id):
    """Patient joins video call with token"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Only patient can join with this endpoint
    if user != appointment.patient:
        messages.error(request, "Invalid access.")
        return redirect('dashboard')
    
    # Check if call has been started by doctor
    if appointment.video_call_status == 'not_started':
        messages.info(request, "The doctor has not started the video call yet. Please wait.")
        return redirect('medical:chat', appointment_id=appointment.id)
    
    # Redirect patient to video call room with their token
    return redirect(f'/medical/appointments/{appointment.id}/video-call/?token={appointment.patient_token}')


@login_required
def end_video_call(request, appointment_id):
    """End video call - can be called by either doctor or patient"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Check permissions
    if not (user == appointment.patient or user == appointment.doctor):
        messages.error(request, "Permission denied.")
        return redirect('dashboard')
    
    # End the call
    if appointment.video_call_status == 'in_progress':
        appointment.end_video_call()
        messages.success(request, "Video call ended.")
    else:
        messages.info(request, "Video call was already ended.")
    
    return redirect('medical:chat', appointment_id=appointment.id)


@login_required
def test_devices(request):
    """Pre-call camera and microphone test page"""
    return render(request, 'medical/video_call_test.html')


@csrf_exempt
def video_call_signal(request, appointment_id):
    """WebRTC signaling endpoint for AJAX-based signaling (fallback)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        signal_type = data.get('type')
        
        # In a production environment, you would broadcast this signal
        # to the other peer via WebSocket or another real-time mechanism
        # For now, we return success and let the WebSocket handle real-time signaling
        
        return JsonResponse({
            'success': True,
            'type': signal_type,
            'message': 'Signal received'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_video_call_status(request, appointment_id):
    """AJAX endpoint to get current video call status"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    if not (user == appointment.patient or user == appointment.doctor):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    return JsonResponse({
        'status': appointment.video_call_status,
        'room_id': appointment.video_call_room_id,
        'started_at': appointment.video_call_started_at.isoformat() if appointment.video_call_started_at else None,
        'duration': appointment.call_duration,
    })
