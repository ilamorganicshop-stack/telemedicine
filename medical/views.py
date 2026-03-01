from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import datetime
from urllib.parse import quote, urlparse
import os
import json
import uuid
from .models import Hospital, DoctorProfile, PatientProfile, Appointment, Availability, ChatMessage, Notification
from accounts.decorators import never_cache

User = get_user_model()
MAX_CHAT_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


def _allowed_return_paths(appointment):
    return {
        reverse('accounts:dashboard'),
        reverse('medical:chat', args=[appointment.id]),
        reverse('medical:patient_chatbox', args=[appointment.id]),
        reverse('medical:doctor_chatbox', args=[appointment.id]),
        reverse('medical:waiting_lobby', args=[appointment.id]),
    }


def _safe_return_to(request, appointment, default_path):
    raw_target = (
        request.GET.get('return_to')
        or request.POST.get('return_to')
        or default_path
    )

    parsed = urlparse(raw_target)
    if parsed.netloc and parsed.netloc != request.get_host():
        return default_path

    target_path = parsed.path if parsed.path else raw_target
    if target_path not in _allowed_return_paths(appointment):
        return default_path

    if parsed.query:
        return f'{target_path}?{parsed.query}'
    return target_path


def _serialize_chat_message(message, current_user):
    local_timestamp = timezone.localtime(message.created_at)
    attachment_url = message.attachment.url if message.attachment else None
    attachment_name = os.path.basename(message.attachment.name) if message.attachment else None
    attachment_size = message.attachment.size if message.attachment else 0
    extension = os.path.splitext(message.attachment.name)[1].lower() if message.attachment else ''
    is_image = extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}

    return {
        'id': message.id,
        'message_id': message.id,
        'message': message.message,
        'sender': f"{message.sender.first_name} {message.sender.last_name}",
        'sender_id': message.sender.id,
        'created_at': local_timestamp.isoformat(),
        'created_at_display': local_timestamp.strftime('%I:%M %p').lstrip('0'),
        'is_self': message.sender_id == current_user.id,
        'has_attachment': bool(message.attachment),
        'attachment_url': attachment_url,
        'attachment_name': attachment_name,
        'attachment_size': attachment_size,
        'is_image': is_image,
    }


@never_cache
@login_required
def hospital_list(request):
    hospitals = Hospital.objects.all()
    return render(request, 'medical/hospital_list.html', {'hospitals': hospitals})


@never_cache
@login_required
def hospital_detail(request, hospital_id):
    hospital = get_object_or_404(Hospital, id=hospital_id)
    doctors = hospital.doctors.all()
    return render(request, 'medical/hospital_detail.html', {'hospital': hospital, 'doctors': doctors})


@never_cache
@login_required
def doctor_list(request):
    # Filter doctors by patient's hospital if user is a patient
    if request.user.is_patient:
        try:
            patient_hospital = request.user.patient_profile.hospital
            doctors = DoctorProfile.objects.select_related('user', 'hospital').filter(hospital=patient_hospital)
        except:
            doctors = DoctorProfile.objects.none()
    else:
        doctors = DoctorProfile.objects.select_related('user', 'hospital').all()
    return render(request, 'medical/doctor_list.html', {'doctors': doctors})


@never_cache
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


@never_cache
@login_required
def patient_list(request):
    if not request.user.is_doctor and not request.user.is_admin_user:
        messages.error(request, "You don't have permission to view patients.")
        return redirect('dashboard')
    
    patients = PatientProfile.objects.select_related('user', 'hospital').all()
    return render(request, 'medical/patient_list.html', {'patients': patients})


@never_cache
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


@never_cache
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


@never_cache
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


@never_cache
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


@never_cache
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


@never_cache
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


@never_cache
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


@never_cache
@login_required
def doctor_chatbox(request, appointment_id):
    """Dedicated chatbox for doctor"""
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor', 'hospital'),
        id=appointment_id
    )
    
    if request.user != appointment.doctor:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard')
    
    return render(request, 'medical/doctor_chatbox.html', {'appointment': appointment})


@never_cache
@login_required
def patient_chatbox(request, appointment_id):
    """Dedicated chatbox for patient"""
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor', 'hospital'),
        id=appointment_id
    )
    
    if request.user != appointment.patient:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard')
    
    return render(request, 'medical/patient_chatbox.html', {'appointment': appointment})


@never_cache
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
    attachment = request.FILES.get('attachment')

    if not message_text and not attachment:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    if attachment and attachment.size > MAX_CHAT_ATTACHMENT_SIZE:
        return JsonResponse({'error': 'File size must be 10MB or less.'}, status=400)
    
    message = ChatMessage.objects.create(
        appointment=appointment,
        sender=user,
        message=message_text,
        attachment=attachment
    )

    response_payload = _serialize_chat_message(message, user)
    response_payload['success'] = True

    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'chat_{appointment.id}',
            {
                'type': 'chat_message',
                **response_payload,
                'sender_name': response_payload['sender'],
            }
        )

    return JsonResponse(response_payload)


@never_cache
@login_required
def get_chat_messages(request, appointment_id):
    """Get chat messages for an appointment (AJAX endpoint)"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    # Check permissions
    if not (user.is_admin_user or user == appointment.patient or user == appointment.doctor):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get messages since a specific time (for polling)
    since = request.GET.get('since')
    messages_query = ChatMessage.objects.filter(appointment=appointment).select_related('sender')
    
    if since:
        normalized_since = since.strip()
        if ' ' in normalized_since and '+' not in normalized_since and 'T' in normalized_since:
            date_part, offset_part = normalized_since.rsplit(' ', 1)
            if ':' in offset_part:
                normalized_since = f'{date_part}+{offset_part}'

        since_time = parse_datetime(normalized_since)
        if since_time:
            if timezone.is_naive(since_time):
                since_time = timezone.make_aware(since_time)
            messages_query = messages_query.filter(created_at__gt=since_time)
    
    messages_query = messages_query.order_by('created_at')
    
    messages_data = [_serialize_chat_message(msg, user) for msg in messages_query]
    
    return JsonResponse({
        'success': True,
        'messages': messages_data
    })


# ==================== VIDEO CALL VIEWS ====================

@never_cache
@login_required
def video_call_view(request, appointment_id):
    """Main video call page for doctor or patient"""
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor', 'hospital'),
        id=appointment_id
    )
    
    user = request.user
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Video call view - User: {user.id} ({user.email}), Role: {user.role}")
    logger.info(f"Appointment doctor: {appointment.doctor.id} ({appointment.doctor.email})")
    logger.info(f"Appointment patient: {appointment.patient.id} ({appointment.patient.email})")
    logger.info(f"Is doctor: {user == appointment.doctor}, Is patient: {user == appointment.patient}")
    
    if not (user == appointment.patient or user == appointment.doctor):
        messages.error(request, "You don't have permission to join this video call.")
        return redirect('accounts:dashboard')
    
    # Determine user type - check by role as backup
    if user == appointment.doctor or user.role == 'doctor':
        user_type = 'doctor'
    else:
        user_type = 'patient'
    
    logger.info(f"Determined user_type: {user_type}")

    # Ensure both participants can join the same room even if patient joins first.
    if not appointment.video_call_room_id:
        appointment.generate_room_id()
        appointment.save()
    
    if user_type == 'doctor' and appointment.video_call_status == 'waiting':
        appointment.start_video_call()

    default_return = (
        reverse('medical:doctor_chatbox', args=[appointment.id])
        if user_type == 'doctor'
        else reverse('medical:patient_chatbox', args=[appointment.id])
    )
    return_to = _safe_return_to(request, appointment, default_return)
    
    webrtc_config = {
        'stun_servers': settings.WEBRTC_STUN_SERVERS,
        'turn_servers': settings.WEBRTC_TURN_SERVERS,
    }
    
    return render(request, 'medical/video_call.html', {
        'appointment': appointment,
        'user_type': user_type,
        'room_id': appointment.video_call_room_id,
        'return_to': return_to,
        'webrtc_config': json.dumps(webrtc_config),
    })


@never_cache
@login_required
def start_video_call(request, appointment_id):
    """Doctor initiates video call"""
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor', 'patient'),
        id=appointment_id
    )
    user = request.user
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if user != appointment.doctor:
        messages.error(request, "Only the doctor can start the video call.")
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Only the doctor can start the video call.'}, status=403)
        return redirect('medical:doctor_chatbox', appointment_id=appointment.id)
    
    if not appointment.video_call_room_id:
        appointment.generate_room_id()
    
    appointment.video_call_status = 'waiting'
    appointment.video_call_started_at = None
    appointment.video_call_ended_at = None
    appointment.call_duration = 0
    appointment.save()

    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'call_invite_{appointment.id}',
            {
                'type': 'call_event',
                'sender_channel': '',
                'payload': {
                    'type': 'call_invite',
                    'appointment_id': appointment.id,
                    'room_id': appointment.video_call_room_id,
                    'sender_id': user.id,
                    'sender_role': 'doctor',
                    'sender_name': f'{user.first_name} {user.last_name}'.strip() or user.email,
                    'timestamp': timezone.now().isoformat(),
                }
            }
        )

    default_return = reverse('medical:doctor_chatbox', args=[appointment.id])
    return_to = _safe_return_to(request, appointment, default_return)
    video_call_url = f"{reverse('medical:video_call', args=[appointment.id])}?return_to={quote(return_to, safe='')}"

    if is_ajax:
        return JsonResponse({
            'success': True,
            'appointment_id': appointment.id,
            'room_id': appointment.video_call_room_id,
            'video_call_url': video_call_url,
            'return_to': return_to,
        })

    return redirect(video_call_url)


@never_cache
@login_required
def join_video_call(request, appointment_id):
    """Patient joins video call"""
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor', 'patient'),
        id=appointment_id
    )
    user = request.user
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if user != appointment.patient:
        messages.error(request, "Invalid access.")
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Invalid access.'}, status=403)
        return redirect('accounts:dashboard')

    waiting_lobby_url = reverse('medical:waiting_lobby', args=[appointment.id])
    if appointment.video_call_status not in {'waiting', 'in_progress'}:
        message = 'Doctor has not started the call yet. Please wait in the waiting lobby or chat.'
        if is_ajax:
            return JsonResponse({'success': False, 'error': message}, status=400)
        messages.warning(request, message)
        return redirect(waiting_lobby_url)

    if not appointment.video_call_room_id:
        appointment.generate_room_id()
        appointment.save()

    return_to = _safe_return_to(request, appointment, waiting_lobby_url)
    video_call_url = f"{reverse('medical:video_call', args=[appointment.id])}?return_to={quote(return_to, safe='')}"

    if is_ajax:
        return JsonResponse({
            'success': True,
            'appointment_id': appointment.id,
            'room_id': appointment.video_call_room_id,
            'video_call_url': video_call_url,
            'return_to': return_to,
        })

    return redirect(video_call_url)


@never_cache
@login_required
def end_video_call(request, appointment_id):
    """End video call - can be called by either doctor or patient"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user
    
    if not (user == appointment.patient or user == appointment.doctor):
        messages.error(request, "Permission denied.")
        return redirect('accounts:dashboard')
    
    if appointment.video_call_status == 'in_progress':
        appointment.end_video_call()
        messages.success(request, "Video call ended.")
    else:
        messages.info(request, "Video call was already ended.")

    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'call_invite_{appointment.id}',
            {
                'type': 'call_event',
                'sender_channel': '',
                'payload': {
                    'type': 'call_ended',
                    'appointment_id': appointment.id,
                    'sender_id': user.id,
                    'sender_role': 'doctor' if user == appointment.doctor else 'patient',
                    'sender_name': f'{user.first_name} {user.last_name}'.strip() or user.email,
                    'timestamp': timezone.now().isoformat(),
                }
            }
        )

    default_return = (
        reverse('medical:doctor_chatbox', args=[appointment.id])
        if user == appointment.doctor
        else reverse('medical:patient_chatbox', args=[appointment.id])
    )
    return_to = _safe_return_to(request, appointment, default_return)
    return redirect(return_to)


@never_cache
@login_required
def test_devices(request):
    """Pre-call camera and microphone test page"""
    return render(request, 'medical/video_call_test.html')


@never_cache
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


@never_cache
@login_required
def waiting_lobby(request, appointment_id):
    """
    Waiting lobby view for patients/doctors before joining a video call.
    Shows a countdown timer until the appointment time.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if user is the patient or doctor for this appointment
    if request.user == appointment.patient:
        template = 'medical/waiting_lobby.html'
    elif request.user == appointment.doctor:
        template = 'medical/doctor_waiting_lobby.html'
    else:
        messages.error(request, 'You do not have permission to access this waiting lobby.')
        return redirect('accounts:dashboard')
    
    # Check if appointment is scheduled, confirmed, or rescheduled
    if appointment.status not in ['scheduled', 'confirmed', 'rescheduled']:
        messages.warning(request, 'This appointment is not scheduled.')
        return redirect('accounts:dashboard')
    
    # Calculate time until appointment
    now = timezone.now()
    time_until_appointment = (appointment.appointment_date - now).total_seconds()
    
    context = {
        'appointment': appointment,
        'time_until_appointment': max(0, time_until_appointment),
        'can_join': time_until_appointment <= 300,
    }
    
    return render(request, template, context)


@never_cache
@login_required
def doctor_patients(request):
    """View list of patients assigned to the doctor"""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    # Get unique patients from completed appointments
    patients = User.objects.filter(
        role='patient',
        patient_appointments__doctor=request.user,
        patient_appointments__status='completed'
    ).distinct().select_related('patient_profile')

    return render(request, 'medical/doctor_patients.html', {'patients': patients})


@never_cache
@login_required
def update_appointment_time(request, appointment_id):
    """Update appointment time from waiting lobby"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions - only doctor can reschedule
    if request.user != appointment.doctor:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        new_time_str = data.get('appointment_date')
        
        if not new_time_str:
            return JsonResponse({'error': 'No appointment date provided'}, status=400)
        
        # Parse the datetime string
        new_time = datetime.fromisoformat(new_time_str.replace('Z', '+00:00'))
        
        # Make timezone aware if needed
        if timezone.is_naive(new_time):
            new_time = timezone.make_aware(new_time)
        
        # Store old date for notification
        old_date = appointment.appointment_date
        
        # Update appointment
        appointment.appointment_date = new_time
        appointment.status = 'rescheduled'
        appointment.save()
        
        # Create notification for patient
        Notification.objects.create(
            recipient=appointment.patient,
            notification_type='appointment_rescheduled',
            title='Appointment Rescheduled',
            message=f'Your appointment has been rescheduled from {old_date.strftime("%B %d, %Y at %I:%M %p")} to {new_time.strftime("%B %d, %Y at %I:%M %p")}.',
            appointment=appointment
        )
        
        return JsonResponse({
            'success': True,
            'new_time': appointment.appointment_date.isoformat()
        })
        
    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Invalid date format: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
