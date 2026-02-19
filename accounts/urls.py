from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Super Admin URLs
    path('super-admin/dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('super-admin/create-hospital/', views.create_hospital, name='create_hospital'),
    path('super-admin/manage-hospitals/', views.manage_hospitals, name='manage_hospitals'),
    path('super-admin/edit-hospital/<int:pk>/', views.edit_hospital, name='edit_hospital'),
    path('super-admin/delete-hospital/<int:pk>/', views.delete_hospital, name='delete_hospital'),
    path('super-admin/create-admin/', views.create_hospital_admin, name='create_hospital_admin'),
    path('super-admin/manage-doctors/', views.super_admin_manage_doctors, name='super_admin_manage_doctors'),
    path('super-admin/manage-patients/', views.super_admin_manage_patients, name='super_admin_manage_patients'),
    path('super-admin/manage-admins/', views.super_admin_manage_admins, name='super_admin_manage_admins'),
    path('super-admin/create-doctor/', views.super_admin_create_doctor, name='super_admin_create_doctor'),
    path('super-admin/create-patient/', views.super_admin_create_patient, name='super_admin_create_patient'),
    path('super-admin/edit-patient/<int:pk>/', views.super_admin_edit_patient, name='super_admin_edit_patient'),
    path('super-admin/delete-patient/<int:pk>/', views.super_admin_delete_patient, name='super_admin_delete_patient'),
    path('super-admin/edit-doctor/<int:pk>/', views.super_admin_edit_doctor, name='super_admin_edit_doctor'),
    path('super-admin/delete-doctor/<int:pk>/', views.super_admin_delete_doctor, name='super_admin_delete_doctor'),
    path('super-admin/edit-admin/<int:pk>/', views.super_admin_edit_admin, name='super_admin_edit_admin'),
    path('super-admin/delete-admin/<int:pk>/', views.super_admin_delete_admin, name='super_admin_delete_admin'),
    
    # Hospital Admin URLs
    path('hospital-admin/dashboard/', views.hospital_admin_dashboard, name='hospital_admin_dashboard'),
    path('hospital-admin/create-doctor/', views.create_doctor, name='create_doctor'),
    path('hospital-admin/create-patient/', views.create_patient, name='create_patient'),
    path('hospital-admin/manage-doctors/', views.manage_doctors, name='manage_doctors'),
    path('hospital-admin/manage-patients/', views.manage_patients, name='manage_patients'),
    path('hospital-admin/edit-patient/<int:pk>/', views.edit_patient, name='edit_patient'),
    path('hospital-admin/delete-patient/<int:pk>/', views.delete_patient, name='delete_patient'),
    path('hospital-admin/edit-doctor/<int:pk>/', views.edit_doctor, name='edit_doctor'),
    path('hospital-admin/delete-doctor/<int:pk>/', views.delete_doctor, name='delete_doctor'),
    
    # Appointment Management URLs
    path('hospital-admin/book-appointment/', views.book_appointment, name='book_appointment'),
    path('hospital-admin/manage-appointments/', views.manage_appointments, name='manage_appointments'),
    
    # Doctor Appointment Approval URLs
    path('doctor/pending-appointments/', views.pending_appointments, name='pending_appointments'),
    path('doctor/approve-reject/<int:appointment_id>/', views.approve_reject_appointment, name='approve_reject_appointment'),
    
    # Khalti Payment URLs
    path('payment/', views.khalti_payment, name='khalti_payment'),
    path('payment/verify/', views.khalti_verify, name='khalti_verify'),
    path('payment/success/', views.payment_success, name='payment_success'),
]
