from django.contrib import admin
from .models import PatientProfile, Doctor, AppointmentSlot, Appointment, ChatMessage, MedicalNote
admin.site.register([PatientProfile, Doctor, AppointmentSlot, Appointment, ChatMessage, MedicalNote])
