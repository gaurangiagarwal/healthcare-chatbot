from django.conf import settings
from django.db import models
from django.utils import timezone

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
    hospital = models.ForeignKey("Hospital", on_delete=models.SET_NULL, null=True, blank=True, related_name="doctors")
    contact_route = models.CharField(max_length=240, blank=True, help_text="A directory URL or hospital contact route; do not enter unverified phone numbers.")
    verification_status = models.CharField(max_length=24, default="demo", choices=[("demo", "Demo data"), ("confirmed", "Hospital confirmed"), ("verified", "Independently verified"), ("unknown", "Unknown"), ("expired", "Expired")])
    def __str__(self): return f"{self.name} — {self.specialization}"

class Hospital(models.Model):
    VERIFICATION_CHOICES = [("demo", "Demo data"), ("confirmed", "Hospital confirmed"), ("verified", "Independently verified"), ("unknown", "Unknown"), ("expired", "Expired")]
    name = models.CharField(max_length=180)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True, help_text="Leave blank unless this is a verified public contact number.")
    website = models.URLField(blank=True)
    verification_status = models.CharField(max_length=24, choices=VERIFICATION_CHOICES, default="demo")
    verification_expires_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["city", "name"]
    @property
    def effective_verification_status(self):
        if self.verification_expires_at and self.verification_expires_at <= timezone.now():
            return "expired"
        if self.is_demo:
            return "demo"
        return self.verification_status
    def __str__(self): return f"{self.name} ({self.city})"

class HospitalService(models.Model):
    SERVICE_CHOICES = [("emergency", "Emergency department"), ("icu", "ICU"), ("trauma", "Trauma care"), ("specialty", "Specialty")]
    STATUS_CHOICES = [("available", "Reported available"), ("unavailable", "Reported unavailable"), ("unknown", "Unknown")]
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="services")
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    specialty_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unknown")
    details = models.CharField(max_length=300, blank=True)
    source = models.CharField(max_length=240, default="Demo data; not confirmed by a hospital")
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hospital_service_updates")
    class Meta:
        ordering = ["service_type", "specialty_name"]
        constraints = [models.UniqueConstraint(fields=["hospital", "service_type", "specialty_name"], name="unique_hospital_service_item")]
    @property
    def effective_status(self):
        if self.expires_at and self.expires_at <= timezone.now():
            return "unknown"
        return self.status
    def __str__(self): return f"{self.hospital.name}: {self.get_service_type_display()} ({self.specialty_name or self.get_status_display()})"

class HospitalAdministrator(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hospital_admin_profile")
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="administrators")
    created_at = models.DateTimeField(auto_now_add=True)

class EmergencyContact(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="emergency_contacts")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    relationship = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["created_at"]

class EmergencyCase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="emergency_cases")
    reported_facts = models.JSONField(default=dict)
    location_shared = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Referral(models.Model):
    STATUS_CHOICES = [("received", "Received"), ("reviewing", "Reviewing"), ("information_requested", "Information requested"), ("acknowledged", "Acknowledged"), ("closed", "Closed")]
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="referrals")
    summary = models.CharField(max_length=1000)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="received")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class HospitalEnquiry(models.Model):
    STATUS_CHOICES = Referral.STATUS_CHOICES
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hospital_enquiries")
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="enquiries")
    message = models.CharField(max_length=1000)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="received")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    administrator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="hospital_audit_events")
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="audit_events")
    action = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ChatConversation(models.Model):
    """A patient's isolated chat thread and its small rule-based context."""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_conversations")
    state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-updated_at"]
    def __str__(self): return f"Chat with {self.patient} ({self.pk})"

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
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
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
