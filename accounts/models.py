from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Hospital Admin'),
        ('super_admin', 'Super Admin'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    hospital = models.ForeignKey('medical.Hospital', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_patient(self):
        return self.role == 'patient'
    
    @property
    def is_doctor(self):
        return self.role == 'doctor'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'
    
    @property
    def is_super_admin(self):
        return self.role == 'super_admin'
