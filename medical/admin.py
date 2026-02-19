from django.contrib import admin
from .models import Hospital, DoctorProfile, PatientProfile, Appointment, Availability


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'email')
    search_fields = ('name', 'address', 'email')
    list_filter = ('created_at',)


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hospital', 'specialization', 'experience_years', 'consultation_fee', 'is_available')
    list_filter = ('specialization', 'is_available', 'hospital', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'specialization', 'license_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hospital', 'blood_type', 'emergency_contact_name')
    list_filter = ('blood_type', 'hospital', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'emergency_contact_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'hospital', 'appointment_date', 'status', 'video_call_status')
    list_filter = ('status', 'video_call_status', 'appointment_date', 'hospital')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__first_name', 'doctor__last_name')
    date_hierarchy = 'appointment_date'
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-appointment_date',)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time', 'is_available')
    list_filter = ('day_of_week', 'is_available', 'doctor')
    search_fields = ('doctor__first_name', 'doctor__last_name')
    readonly_fields = ('created_at', 'updated_at')
