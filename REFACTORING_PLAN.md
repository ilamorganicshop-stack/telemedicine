# REFACTORING PLAN - Multi Hospital System

## Current Status Check

### ✅ Payment Flow - VERIFIED
- [x] Admin creates patient with "Mark as Paid" option
- [x] Unpaid patient redirected to Khalti payment on login
- [x] Payment verification via Khalti API
- [x] Success page with auto-redirect
- [x] Admin cannot revert paid status

## Required Changes

### 1. Remove Username Field (Use Email for Login)
**Impact**: HIGH - Affects authentication system
**Files to modify**:
- `accounts/models.py` - Make username auto-generated from email
- `accounts/forms.py` - Remove username from all forms
- `accounts/admin_forms.py` - Remove username fields
- `accounts/views.py` - Already uses email for login ✅
- All templates - Remove username display/input

**Implementation**:
```python
# In User model save method
def save(self, *args, **kwargs):
    if not self.username:
        self.username = self.email.split('@')[0] + str(self.id or '')
    super().save(*args, **kwargs)
```

### 2. Hospital Admin Sets Appointment Price
**Impact**: MEDIUM
**Files to modify**:
- `medical/models.py` - Add `appointment_fee` to Hospital model
- `accounts/admin_forms.py` - Add appointment_fee to HospitalForm
- Patient payment flow - Change from registration_fee to appointment_fee

**New Fields**:
```python
class Hospital(models.Model):
    appointment_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1000.00,
        help_text="Fee per appointment in NPR"
    )
```

### 3. Patient Pays Appointment Price (Not Registration)
**Impact**: HIGH - Changes payment model
**Files to modify**:
- `medical/models.py` - Remove registration_fee from PatientProfile
- `accounts/views.py` - Change payment logic to appointment-based
- `accounts/templates/accounts/khalti_payment.html` - Update UI

**New Flow**:
- Patient books appointment → Redirected to payment
- Payment amount = Hospital.appointment_fee
- After payment → Appointment status = 'confirmed'

### 4. Remove Fees from Doctor Creation
**Impact**: LOW
**Files to modify**:
- `accounts/admin_forms.py` - Remove consultation_fee field
- `medical/models.py` - Remove consultation_fee from DoctorProfile

### 5. Remove Website from Hospital Creation
**Impact**: LOW
**Files to modify**:
- `medical/models.py` - Make website field optional or remove
- `accounts/admin_forms.py` - Remove from HospitalForm

### 6. Hospital Admin CRUD for Patients/Doctors
**Impact**: MEDIUM - Add edit/delete views
**Files to add**:
- `accounts/views.py` - Add edit_patient, delete_patient, edit_doctor, delete_doctor
- `accounts/urls.py` - Add CRUD URLs
- Templates - Add edit forms and delete confirmations

**URLs to add**:
```python
path('hospital-admin/edit-patient/<int:pk>/', views.edit_patient, name='edit_patient'),
path('hospital-admin/delete-patient/<int:pk>/', views.delete_patient, name='delete_patient'),
path('hospital-admin/edit-doctor/<int:pk>/', views.edit_doctor, name='edit_doctor'),
path('hospital-admin/delete-doctor/<int:pk>/', views.delete_doctor, name='delete_doctor'),
```

### 7. Super Admin CRUD for All Users
**Impact**: MEDIUM
**Files to modify**:
- `accounts/views.py` - Add edit/delete views for all user types
- `accounts/urls.py` - Add super admin CRUD URLs
- Templates - Add management interfaces

## Implementation Priority

### Phase 1 (Critical - Do First)
1. Remove username field → Use email
2. Hospital admin sets appointment price
3. Change payment from registration to appointment-based

### Phase 2 (Important)
4. Remove doctor consultation fee
5. Remove hospital website field
6. Add CRUD operations for hospital admin

### Phase 3 (Enhancement)
7. Add CRUD operations for super admin

## Migration Steps

1. Create new migration for model changes
2. Data migration to populate usernames from emails
3. Update all forms to remove username
4. Update templates
5. Test authentication flow
6. Deploy

## Testing Checklist

- [ ] Email-based login works
- [ ] Patient can book appointment
- [ ] Payment redirects to Khalti with correct amount
- [ ] Payment verification works
- [ ] Hospital admin can edit/delete patients
- [ ] Hospital admin can edit/delete doctors
- [ ] Super admin has full CRUD access
- [ ] No username fields visible in UI

## Rollback Plan

If issues occur:
1. Keep username field but hide in UI
2. Revert to registration fee model
3. Restore old forms from git history

---

**Status**: Ready for implementation
**Estimated Time**: 4-6 hours
**Risk Level**: Medium-High (authentication changes)
