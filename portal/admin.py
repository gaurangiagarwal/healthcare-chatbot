from django.contrib import admin
from .models import (
    PatientProfile, Doctor, AppointmentSlot, Appointment, ChatMessage, MedicalNote,
    Hospital, HospitalService, HospitalAdministrator, HospitalEnquiry, Referral, AuditLog,
)

admin.site.register([
    PatientProfile, Doctor, AppointmentSlot, Appointment, ChatMessage, MedicalNote,
    Hospital, HospitalService, HospitalAdministrator, HospitalEnquiry, Referral, AuditLog,
])
