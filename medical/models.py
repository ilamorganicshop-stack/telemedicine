import uuid
from django.db import models
from django.conf import settings
from django.core.validators import EmailValidator, RegexValidator


class Hospital(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    appointment_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1000.00,
        help_text="Fee per appointment in NPR"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Hospital"
        verbose_name_plural = "Hospitals"


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='doctor_profile'
    )
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctors')
    license_number = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=200)
    experience_years = models.PositiveIntegerField()
    bio = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to='doctor_profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} - {self.specialization}"
    
    class Meta:
        verbose_name = "Doctor Profile"
        verbose_name_plural = "Doctor Profiles"


class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='patient_profile'
    )
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='patients')
    medical_history = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    blood_type = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        blank=True,
        null=True
    )
    # Payment fields - removed registration_fee, now uses hospital appointment_fee
    payment_status = models.BooleanField(default=False, help_text="Whether patient has paid for appointments")
    khalti_transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="Khalti transaction reference")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - Patient"
    
    class Meta:
        verbose_name = "Patient Profile"
        verbose_name_plural = "Patient Profiles"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('pending_approval', 'Pending Approval'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    VIDEO_CALL_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('waiting', 'Waiting for Doctor'),
        ('in_progress', 'In Progress'),
        ('ended', 'Ended'),
    ]
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='patient_appointments'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='doctor_appointments'
    )
    hospital = models.ForeignKey(
        Hospital, 
        on_delete=models.CASCADE, 
        related_name='appointments'
    )
    appointment_date = models.DateTimeField()
    symptoms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='requested'
    )
    
    # Video call fields
    video_call_room_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Unique room ID for video call",
        unique=True
    )
    video_call_status = models.CharField(
        max_length=20,
        choices=VIDEO_CALL_STATUS_CHOICES,
        default='not_started',
        help_text="Current status of the video call"
    )
    video_call_started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the video call started"
    )
    video_call_ended_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the video call ended"
    )
    recording_enabled = models.BooleanField(
        default=False,
        help_text="Whether call recording is enabled (requires patient consent)"
    )
    screen_sharing_active = models.BooleanField(
        default=False,
        help_text="Whether screen sharing is currently active"
    )
    call_duration = models.PositiveIntegerField(
        default=0,
        help_text="Call duration in seconds"
    )
    
    # Existing fields
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_appointments',
        help_text="Admin who requested this appointment"
    )
    rejection_reason = models.TextField(
        blank=True, 
        null=True,
        help_text="Reason for rejection by doctor"
    )
    
    # Doctor's proposed date/time change fields
    doctor_proposed_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Doctor's proposed new date/time for the appointment"
    )
    doctor_change_requested = models.BooleanField(
        default=False,
        help_text="Whether doctor has requested a date/time change"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Appointment: {self.patient.first_name} {self.patient.last_name} with Dr. {self.doctor.first_name} {self.doctor.last_name} on {self.appointment_date.strftime('%Y-%m-%d %H:%M')}"
    
    def generate_room_id(self):
        """Generate a unique room ID for video call"""
        self.video_call_room_id = str(uuid.uuid4())
        return self.video_call_room_id
    
    def start_video_call(self):
        """Mark video call as started"""
        from django.utils import timezone
        self.video_call_status = 'in_progress'
        self.video_call_started_at = timezone.now()
        self.save()
    
    def end_video_call(self):
        """Mark video call as ended and calculate duration"""
        from django.utils import timezone
        self.video_call_status = 'ended'
        self.video_call_ended_at = timezone.now()
        if self.video_call_started_at:
            duration = (self.video_call_ended_at - self.video_call_started_at).total_seconds()
            self.call_duration = int(duration)
        self.save()
    
    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ['appointment_date']


class Availability(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='availability'
    )
    day_of_week = models.PositiveSmallIntegerField(
        choices=[
            (0, 'Monday'),
            (1, 'Tuesday'),
            (2, 'Wednesday'),
            (3, 'Thursday'),
            (4, 'Friday'),
            (5, 'Saturday'),
            (6, 'Sunday'),
        ]
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dr. {self.doctor.first_name} {self.doctor.last_name} - {self.get_day_of_week_display()} ({self.start_time} - {self.end_time})"
    
    class Meta:
        verbose_name = "Availability"
        verbose_name_plural = "Availabilities"
        unique_together = ['doctor', 'day_of_week']


class ChatMessage(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='chat_messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    message = models.TextField()
    attachment = models.FileField(
        upload_to='chat_attachments/%Y/%m/%d/',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.sender.first_name} {self.sender.last_name}: {self.message[:50]}..."
    
    class Meta:
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ['created_at']


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('appointment_approved', 'Appointment Approved'),
        ('appointment_rejected', 'Appointment Rejected'),
        ('appointment_rescheduled', 'Appointment Rescheduled by Doctor'),
        ('appointment_requested', 'New Appointment Request'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.notification_type} - {self.recipient.username}"
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
