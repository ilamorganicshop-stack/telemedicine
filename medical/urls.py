from django.urls import path
from . import views

app_name = 'medical'

urlpatterns = [
    # Hospitals
    path('hospitals/', views.hospital_list, name='hospital_list'),
    path('hospitals/<int:hospital_id>/', views.hospital_detail, name='hospital_detail'),
    
    # Doctors
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    
    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    
    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/create/', views.create_appointment, name='create_appointment'),
    path('appointments/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    
    # Chat
    path('appointments/<int:appointment_id>/chat/', views.chat_view, name='chat'),
    path('appointments/<int:appointment_id>/send-message/', views.send_message, name='send_message'),
    path('appointments/<int:appointment_id>/get-messages/', views.get_chat_messages, name='get_chat_messages'),
    
    # Video Call
    path('appointments/<int:appointment_id>/video-call/', views.video_call_view, name='video_call'),
    path('appointments/<int:appointment_id>/video-call/start/', views.start_video_call, name='start_video_call'),
    path('appointments/<int:appointment_id>/video-call/join/', views.join_video_call, name='join_video_call'),
    path('appointments/<int:appointment_id>/video-call/end/', views.end_video_call, name='end_video_call'),
    path('appointments/<int:appointment_id>/video-call/status/', views.get_video_call_status, name='video_call_status'),
    path('appointments/<int:appointment_id>/video-call/signal/', views.video_call_signal, name='video_call_signal'),
    path('video-call/test-devices/', views.test_devices, name='test_devices'),
    
    # Waiting Lobby
    path('appointments/<int:appointment_id>/waiting-lobby/', views.waiting_lobby, name='waiting_lobby'),
]
