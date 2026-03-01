# How to See the Changes on Local Server

The code has been updated successfully. To see the changes:

## Step 1: Restart Your Django Server

If your Django development server is running, you need to restart it:

1. **Stop the server**: Press `Ctrl + C` in the terminal where the server is running
2. **Start the server again**:
   ```bash
   python manage.py runserver
   ```

## Step 2: Clear Browser Cache (Important!)

Django templates are sometimes cached by the browser. To see the changes:

1. **Hard refresh** your browser:
   - **Windows/Linux**: Press `Ctrl + Shift + R` or `Ctrl + F5`
   - **Mac**: Press `Cmd + Shift + R`

OR

2. **Clear browser cache**:
   - Open browser settings
   - Clear browsing data
   - Select "Cached images and files"
   - Clear data

## Step 3: Log Out and Log Back In

1. Log out from the patient account
2. Log back in as the patient (birami@gmail.com)
3. You should now see the scheduled appointment in the dashboard

## What You Should See

After following these steps, the patient dashboard should show:

1. **Upcoming Appointments count**: Should show "1" instead of "0"
2. **Upcoming Appointments table**: Should display the appointment with:
   - Doctor name and specialization
   - Date and time
   - Status badge (green "Scheduled")
   - View Details link

## Troubleshooting

If you still don't see the appointment:

1. **Check the appointment status in database**:
   ```bash
   python manage.py shell -c "from medical.models import Appointment; a = Appointment.objects.get(id=3); print(f'Status: {a.status}, Date: {a.appointment_date}')"
   ```

2. **Verify the patient**:
   ```bash
   python manage.py shell -c "from medical.models import Appointment; a = Appointment.objects.get(id=3); print(f'Patient: {a.patient.email}')"
   ```

3. **Check if Django is using the updated template**:
   - Look for the file: `accounts/templates/accounts/patient_dashboard.html`
   - Verify it contains `{{ upcoming_appointments_count }}` instead of hardcoded "0"
