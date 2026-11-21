from django.conf import settings
from django.db import models

class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    health_information = models.TextField(blank=True)
    def __str__(self): return self.user.get_full_name() or self.user.username

class Doctor(models.Model):
    name = models.CharField(max_length=120)
    specialization = models.CharField(max_length=100)
    experience = models.PositiveSmallIntegerField(default=0)
    qualification = models.CharField(max_length=120)
    fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    bio = models.TextField(blank=True)
    def __str__(self): return f"{self.name} — {self.specialization}"

class AppointmentSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="slots")
    starts_at = models.DateTimeField()
    class Meta:
        ordering = ["starts_at"]
        constraints = [models.UniqueConstraint(fields=["doctor", "starts_at"], name="unique_doctor_slot")]
    def __str__(self): return f"{self.doctor.name} {self.starts_at:%Y-%m-%d %H:%M}"

class Appointment(models.Model):
    STATUS_CHOICES = [("booked", "Booked"), ("cancelled", "Cancelled"), ("completed", "Completed")]
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments")
    slot = models.ForeignKey(AppointmentSlot, on_delete=models.PROTECT, related_name="appointments")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="booked")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["slot"], condition=models.Q(status="booked"), name="unique_active_slot_booking")]
        ordering = ["-slot__starts_at"]

class ChatMessage(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    role = models.CharField(max_length=10, choices=[("user", "Patient"), ("bot", "Assistant")])
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["created_at"]

class MedicalNote(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medical_notes")
    title = models.CharField(max_length=120)
    body = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
