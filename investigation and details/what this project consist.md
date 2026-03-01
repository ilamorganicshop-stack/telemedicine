# Multi-Hospital Telemedicine Platform - Project Documentation

## Project Overview

This is a **comprehensive Multi-Hospital Telemedicine Platform** built with Django that enables remote healthcare consultations between doctors and patients across multiple hospitals. The platform supports real-time HD video calling, appointment scheduling, secure messaging, and integrated payment processing.

## What This Project Consists Of

### 1. Core Applications

#### **accounts** - User Management & Authentication
- **Custom User Model** (`accounts/models.py`): Extended Django AbstractUser with roles (Patient, Doctor, Hospital Admin, Super Admin)
- **Authentication System**: Login/logout with role-based access control
- **User Profiles**:
  - DoctorProfile: License number, specialization, experience, availability
  - PatientProfile: Medical history, allergies, emergency contacts, blood type, payment status
- **Admin Management**: Super admin can create hospital admins, doctors, and patients
- **Hospital Management**: Multi-hospital support with separate data isolation

#### **medical** - Core Medical Functionality
- **Hospital Model**: Multi-tenant architecture supporting multiple hospitals
- **Appointment System**: Complete appointment lifecycle (request → approval → scheduling → completion)
- **Availability Management**: Doctor schedule management with day/time slots
- **Chat System**: Real-time messaging between doctors and patients with file attachments
- **Notification System**: Automated notifications for appointment updates
- **Video Calling**: HD WebRTC-based video consultations

### 2. Key Features

#### **A. Multi-Hospital Architecture**
- Each hospital operates independently
- Hospital admins manage their own doctors and patients
- Super admin oversees all hospitals
- Data isolation between hospitals

#### **B. Role-Based Access Control**
1. **Super Admin**: Full system access, creates hospitals and hospital admins
2. **Hospital Admin**: Manages doctors and patients within their hospital
3. **Doctor**: Views appointments, manages availability, conducts video calls
4. **Patient**: Books appointments, makes payments, joins video calls

#### **C. Appointment Management**
- Patients request appointments with specific doctors
- Doctors approve/reject with optional date change proposals
- Real-time status tracking (Requested → Pending → Scheduled → Confirmed → In Progress → Completed)
- Conflict detection to prevent double-booking

#### **D. HD Video Calling System** (WebRTC + Django Channels)
- **Technology**: WebRTC peer-to-peer with Django Channels for signaling
- **Features**:
  - HD video quality (720p/1080p)
  - Mute/unmute audio and video
  - Screen sharing (doctor only)
  - In-call text chat
  - Waiting room for patients
  - Connection quality indicator
  - Call duration tracking
- **Security**: Token-based access with 24-hour expiry
- **Infrastructure**: Redis channel layer for WebSocket communication

#### **E. Real-Time Chat**
- WebSocket-based instant messaging
- File attachments support
- Message persistence
- Read receipts

#### **F. Payment Integration (Khalti)**
- Khalti ePayment API v2 integration
- Patients must pay before accessing appointments
- Payment status tracking
- Transaction ID storage

### 3. Technology Stack

#### **Backend**
- **Framework**: Django 5.1.3
- **Database**: PostgreSQL (production) / SQLite (development)
- **Real-Time**: Django Channels 4.2.0 + Redis
- **Video Calling**: WebRTC with STUN/TURN servers
- **Payment**: Khalti Payment Gateway
- **WSGI/ASGI**: Gunicorn + Daphne

#### **Frontend**
- **Templates**: Django Template Engine
- **Styling**: Tailwind CSS (via CDN)
- **JavaScript**: Vanilla JS for WebRTC and WebSocket handling
- **Icons**: Font Awesome

#### **Infrastructure**
- **Containerization**: Docker + Docker Compose
- **Static Files**: WhiteNoise
- **Media Storage**: Local filesystem (development) / Cloud (production)
- **Database**: Supabase PostgreSQL (production)

#### **Dependencies** (from requirements.txt)
```
Django==5.1.3
gunicorn==23.0.0
whitenoise==6.9.0
Pillow==11.1.0
psycopg2-binary==2.9.9
dj-database-url==2.1.0
requests==2.31.0
channels==4.2.0
channels-redis==4.2.0
daphne==4.1.2
django-cors-headers==4.6.0
```

### 4. Database Models & Relationships

```
User (AbstractUser)
├── role: patient/doctor/admin/super_admin
├── hospital: ForeignKey to Hospital
├── doctor_profile → DoctorProfile
└── patient_profile → PatientProfile

Hospital
├── name, address, phone, email
├── appointment_fee: Decimal
├── doctors → DoctorProfile[]
├── patients → PatientProfile[]
└── appointments → Appointment[]

DoctorProfile
├── user: OneToOne
├── hospital: ForeignKey
├── license_number, specialization, experience_years
├── is_available: Boolean
├── profile_picture: ImageField
└── availability → Availability[]

PatientProfile
├── user: OneToOne
├── hospital: ForeignKey
├── medical_history, allergies
├── emergency_contact
├── blood_type
├── payment_status: Boolean
└── khalti_transaction_id

Appointment
├── patient: ForeignKey to User
├── doctor: ForeignKey to User
├── hospital: ForeignKey
├── appointment_date: DateTime
├── status: requested/pending/scheduled/confirmed/in_progress/completed/cancelled/rejected
├── symptoms, notes
├── video_call_room_id: UUID
├── video_call_status: not_started/waiting/in_progress/ended
├── video_call_started_at/ended_at
├── call_duration: Integer (seconds)
├── rejection_reason
├── doctor_proposed_date (for rescheduling)
└── chat_messages → ChatMessage[]

ChatMessage
├── appointment: ForeignKey
├── sender: ForeignKey to User
├── message: Text
├── attachment: FileField
└── is_read: Boolean

Availability
├── doctor: ForeignKey
├── day_of_week: 0-6
├── start_time, end_time
└── is_available: Boolean

Notification
├── recipient: ForeignKey to User
├── notification_type
├── title, message
├── appointment: ForeignKey
└── is_read: Boolean
```

### 5. How This Project Runs

#### **Local Development (Without Docker)**

1. **Prerequisites**:
   - Python 3.11+
   - Redis server (for WebSocket support)
   - Virtual environment

2. **Setup Steps**:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run migrations
   python manage.py migrate
   
   # Create super admin
   python manage.py create_superadmin
   
   # Start Redis server (in separate terminal)
   redis-server
   
   # Run development server
   python manage.py runserver
   ```

3. **Access the application**:
   - Main app: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

#### **Local Development (With Docker)**

1. **Prerequisites**:
   - Docker Desktop
   - Docker Compose

2. **Setup Steps**:
   ```bash
   # Build and run containers
   docker compose up --build
   
   # Or run in background
   docker compose up -d --build
   ```

3. **Services started**:
   - Django application on port 8000
   - Health check available at `/accounts/login/`

### 6. How Deployment Is Done

#### **Docker Deployment (Production)**

The project uses **Docker Compose** for containerized deployment:

1. **Dockerfile** (`Dockerfile`):
   - Base image: `python:3.11-slim`
   - Installs system dependencies (gcc, curl)
   - Installs Python requirements
   - Collects static files
   - Runs migrations and creates super admin on startup
   - Uses Gunicorn as WSGI server

2. **Docker Compose** (`compose.yaml`):
   ```yaml
   services:
     telemedicine:
       build:
         context: .
         dockerfile: Dockerfile
       ports:
         - "8000:8000"
       environment:
         - DEBUG=False
         - SECRET_KEY=${SECRET_KEY}
         - ALLOWED_HOSTS=${ALLOWED_HOSTS:-*}
         - DATABASE_URL=postgresql://...
         - KHALTI_PUBLIC_KEY=${KHALTI_PUBLIC_KEY}
         - KHALTI_SECRET_KEY=${KHALTI_SECRET_KEY}
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/accounts/login/"]
         interval: 30s
         timeout: 10s
         retries: 3
   ```

3. **Environment Variables**:
   - `DEBUG`: Set to `False` in production
   - `SECRET_KEY`: Django secret key (change in production)
   - `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
   - `DATABASE_URL`: PostgreSQL connection string (Supabase)
   - `KHALTI_PUBLIC_KEY` / `KHALTI_SECRET_KEY`: Payment gateway credentials
   - `REDIS_URL`: Redis connection string (for WebSocket)

4. **Database**:
   - Production uses **Supabase PostgreSQL**
   - Connection via `DATABASE_URL` environment variable
   - Migrations run automatically on container startup

5. **Static Files**:
   - WhiteNoise serves static files in production
   - `STATIC_ROOT` collects all static files
   - `CompressedManifestStaticFilesStorage` for optimization

6. **Media Files**:
   - User uploads stored in `media/` directory
   - In production, should use cloud storage (AWS S3, etc.)

7. **WebSocket/ASGI**:
   - Uses Daphne ASGI server
   - Redis channel layer for multi-instance support
   - WebRTC requires HTTPS in production

#### **Deployment Steps**:

1. **Build the image**:
   ```bash
   docker compose build
   ```

2. **Run migrations** (automatic on startup):
   ```bash
   docker compose up
   ```

3. **Deploy with Defang (Default)**:
   ```bash
   defang compose up --stack=beta
   ```

4. **Health Check**:

   - Endpoint: `/accounts/login/`
   - Checks every 30 seconds
   - 3 retries before marking unhealthy

5. **Production Checklist**:

   - [ ] Set `DEBUG=False`
   - [ ] Change `SECRET_KEY`
   - [ ] Configure `ALLOWED_HOSTS`
   - [ ] Set up HTTPS (required for WebRTC)
   - [ ] Configure TURN servers for WebRTC
   - [ ] Set up Redis server
   - [ ] Configure PostgreSQL database
   - [ ] Set up media file storage (S3)
   - [ ] Enable CSRF protection
   - [ ] Configure rate limiting

### 7. Project Structure

```
Multi Hospital/
├── accounts/                    # User management app
│   ├── models.py               # User, DoctorProfile, PatientProfile
│   ├── views.py                # Authentication & dashboard views
│   ├── urls.py                 # URL routing
│   ├── forms.py                # Authentication forms
│   ├── admin.py                # Admin configurations
│   ├── admin_forms.py          # Custom admin forms
│   ├── templates/accounts/     # All account-related templates
│   └── management/commands/    # Custom commands (create_superadmin)
├── medical/                     # Core medical functionality
│   ├── models.py               # Hospital, Appointment, ChatMessage, etc.
│   ├── views.py                # Medical views (appointments, video calls)
│   ├── urls.py                 # URL routing
│   ├── consumers.py            # WebSocket consumers (VideoCallConsumer)
│   ├── routing.py              # WebSocket routing
│   ├── admin.py                # Admin configurations
│   └── templates/medical/      # Medical templates (chat, video_call)
├── telemedicine/                # Project configuration
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI application
│   └── asgi.py                 # ASGI application (Channels)
├── media/                       # User uploads (profile pictures, attachments)
├── staticfiles/                 # Collected static files
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image configuration
├── compose.yaml                 # Docker Compose configuration
├── manage.py                    # Django management script
└── investigation and details/   # Project documentation (this folder)
```

### 8. Key URLs & Endpoints

#### **Authentication**
- `/accounts/login/` - Login page
- `/accounts/signup/` - Patient registration
- `/accounts/logout/` - Logout

#### **Dashboards**
- `/accounts/super-admin/dashboard/` - Super Admin dashboard
- `/accounts/hospital-admin/dashboard/` - Hospital Admin dashboard
- `/accounts/doctor/dashboard/` - Doctor dashboard
- `/accounts/patient/dashboard/` - Patient dashboard

#### **Appointments**
- `/medical/appointments/book/` - Book appointment (patient)
- `/medical/appointments/` - List appointments
- `/medical/appointments/<id>/approve/` - Approve appointment (doctor)
- `/medical/appointments/<id>/reject/` - Reject appointment (doctor)

#### **Video Calling**
- `/medical/appointments/<id>/video-call/` - Video call room
- `/medical/appointments/<id>/video-call/start/` - Start call (doctor)
- `/medical/appointments/<id>/video-call/join/` - Join call (patient)
- `/medical/appointments/<id>/video-call/end/` - End call
- `/medical/video-call/test-devices/` - Test camera/microphone

#### **Chat**
- `/medical/appointments/<id>/chat/` - Appointment chat room

#### **Payment**
- `/accounts/payment/` - Khalti payment page
- `/accounts/payment/success/` - Payment success callback
- `/accounts/payment/failed/` - Payment failure page

#### **WebSocket**
- `ws://<host>/ws/video-call/<room_id>/` - Video call WebSocket
- `ws://<host>/ws/chat/<appointment_id>/` - Chat WebSocket

### 9. Security Features

- **CSRF Protection**: Enabled on all forms
- **Role-Based Permissions**: Decorators restrict access by user role
- **Token-Based Video Access**: UUID tokens with 24-hour expiry
- **WebSocket Authentication**: Django Channels auth middleware
- **CORS Headers**: Configured for WebRTC
- **Environment Variables**: Sensitive data not hardcoded
- **SQL Injection Prevention**: Django ORM used throughout
- **XSS Prevention**: Template escaping enabled

### 10. Development Workflow

The project follows an 11-step development flow:

1. **Foundation**: Django setup + Authentication
2. **Models & Database**: Hospital, Doctor, Patient, Appointments
3. **Templates**: Dashboards and views
4. **Scheduling**: Appointment logic and conflict detection
5. **Styling**: Tailwind CSS implementation
6. **Basic Chat**: REST/polling chat
7. **Real-Time Chat**: WebSocket implementation
8. **Lobby System**: Waiting room logic
9. **WebRTC Video**: HD video calling (8 sub-steps)
10. **File Upload**: Medical document sharing
11. **Security & Deployment**: Production readiness

### 11. Testing

- **Unit Tests**: Django test framework
- **Manual Testing**: Video call device testing page
- **Health Checks**: Docker healthcheck endpoint
- **Payment Testing**: Khalti test environment

### 12. Future Enhancements

- Call recording with patient consent
- Virtual backgrounds for video calls
- Multi-party consultations
- Mobile app (iOS/Android)
- AI-powered transcription
- Analytics dashboard

---

## Summary

This Multi-Hospital Telemedicine Platform is a production-ready Django application that enables remote healthcare consultations. It features a robust multi-tenant architecture, real-time HD video calling via WebRTC, integrated payment processing, and comprehensive role-based access control. The platform is containerized with Docker for easy deployment and uses modern technologies like Django Channels and Redis for real-time communication.
