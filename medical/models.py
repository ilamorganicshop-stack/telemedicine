from django.db import models
from django.conf import settings
from django.core.validators import EmailValidator, RegexValidator


class Hospital(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
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
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    bio = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
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
    payment_status = models.BooleanField(default=False, help_text="Whether the patient has paid the registration fee")
    khalti_transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="Khalti transaction ID for verification")
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, help_text="Registration fee amount in NPR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} (Patient)"
    
    class Meta:
        verbose_name = "Patient Profile"
        verbose_name_plural = "Patient Profiles"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),          # Admin booked appointment for patient
        ('pending_approval', 'Pending Approval'), # Waiting for doctor approval
        ('scheduled', 'Scheduled'),           # Doctor approved and scheduled
        ('confirmed', 'Confirmed'),           # Patient confirmed the appointment
        ('in_progress', 'In Progress'),      # Appointment in progress
        ('completed', 'Completed'),           # Appointment completed
        ('cancelled', 'Cancelled'),           # Cancelled by patient/admin
        ('rejected', 'Rejected'),             # Rejected by doctor
        ('no_show', 'No Show'),            # Patient didn't show up
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
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    symptoms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_status = models.BooleanField(default=False)
    requested_by_admin = models.ForeignKey(
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Appointment: {self.patient.first_name} {self.patient.last_name} with Dr. {self.doctor.first_name} {self.doctor.last_name} on {self.appointment_date.strftime('%Y-%m-%d %H:%M')}"
    
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
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.sender.first_name} {self.sender.last_name}: {self.message[:50]}..."
    
    class Meta:
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ['created_at']
