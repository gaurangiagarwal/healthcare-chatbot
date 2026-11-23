from django.conf import settings
from django.core.exceptions import ValidationError
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
    registration_number = models.CharField(max_length=128, blank=True, default="")
    professional_status = models.CharField(max_length=12, choices=[("active", "Active"), ("inactive", "Inactive"), ("unknown", "Unknown")], default="unknown")
    specialties = models.ManyToManyField("Specialty", through="DoctorSpecialty", related_name="doctors", blank=True)
    facilities = models.ManyToManyField("Hospital", through="DoctorHospitalAffiliation", related_name="affiliated_doctors", blank=True)
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
    facility_type = models.CharField(max_length=24, choices=[("hospital", "Hospital"), ("clinic", "Clinic"), ("diagnostic_centre", "Diagnostic centre"), ("imaging_centre", "Imaging centre"), ("pharmacy", "Pharmacy"), ("other", "Other")], null=True, blank=True, default=None)
    operational_status = models.CharField(max_length=24, choices=[("operational", "Operational"), ("temporarily_closed", "Temporarily closed"), ("permanently_closed", "Permanently closed"), ("unknown", "Unknown")], default="unknown")
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


class Specialty(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "name"], name="specialty_active_name_idx")]


class ProviderSourceRecord(models.Model):
    SOURCE_TYPES = [("imported", "Imported"), ("provider_submission", "Provider submission"), ("manual_entry", "Manual entry"), ("demo_data", "Demo data"), ("legacy_unattributed", "Legacy unattributed"), ("other", "Other")]
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, null=True, blank=True, related_name="source_records")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, null=True, blank=True, related_name="source_records")
    source_type = models.CharField(max_length=24, choices=SOURCE_TYPES)
    external_id = models.CharField(max_length=255, blank=True, default="")
    source_name = models.CharField(max_length=120)
    source_url = models.URLField(blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="provider_source_submissions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(doctor__isnull=False, hospital__isnull=True) | models.Q(doctor__isnull=True, hospital__isnull=False)), name="provider_source_one_owner"),
            models.UniqueConstraint(fields=["source_type", "source_name", "external_id"], condition=~models.Q(external_id=""), name="prov_src_external_id_uniq"),
        ]
        indexes = [models.Index(fields=["doctor", "source_type"], name="provsource_doc_type_idx"), models.Index(fields=["hospital", "source_type"], name="provsource_hosp_type_idx")]

    def clean(self):
        super().clean()
        if bool(self.doctor_id) == bool(self.hospital_id):
            raise ValidationError("A source record must belong to exactly one doctor or hospital.")


class DoctorSpecialty(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="specialty_links")
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, related_name="doctor_links")
    is_primary = models.BooleanField(default=False)
    source_record = models.ForeignKey(ProviderSourceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="doctor_specialty_links")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["doctor", "specialty"], name="doctor_specialty_uniq"), models.UniqueConstraint(fields=["doctor"], condition=models.Q(is_primary=True), name="doctor_one_primary_specialty")]
        indexes = [models.Index(fields=["specialty", "doctor"], name="docspecialty_spec_doc_idx")]

    def clean(self):
        super().clean()
        if self.source_record_id and self.source_record.doctor_id != self.doctor_id:
            raise ValidationError({"source_record": "Source record must belong to this doctor."})


class DoctorHospitalAffiliation(models.Model):
    RELATIONSHIP_TYPES = [("employed", "Employed"), ("visiting", "Visiting"), ("consulting", "Consulting"), ("other", "Other"), ("unknown", "Unknown")]
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="affiliations")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="doctor_affiliations")
    relationship_type = models.CharField(max_length=24, choices=RELATIONSHIP_TYPES, default="unknown")
    is_primary = models.BooleanField(default=False)
    is_current = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    source_record = models.ForeignKey(ProviderSourceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="affiliations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["doctor", "hospital"], condition=models.Q(is_current=True), name="doctor_current_facility_uniq"),
            models.UniqueConstraint(fields=["doctor"], condition=models.Q(is_current=True, is_primary=True), name="doctor_one_current_primary_facility"),
            models.CheckConstraint(condition=(models.Q(valid_from__isnull=True) | models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=models.F("valid_from"))), name="doctor_affiliation_valid_dates"),
        ]
        indexes = [models.Index(fields=["doctor", "is_current"], name="affiliation_doc_current_idx"), models.Index(fields=["hospital", "is_current"], name="affiliation_hosp_current_idx")]

    def clean(self):
        super().clean()
        if self.is_primary and not self.is_current:
            raise ValidationError({"is_primary": "Only a current affiliation can be primary."})
        if self.source_record_id and self.source_record.doctor_id != self.doctor_id and self.source_record.hospital_id != self.hospital_id:
            raise ValidationError({"source_record": "Source record must belong to this doctor or this hospital."})


class ProviderVerification(models.Model):
    VERIFICATION_TYPES = [("identity", "Identity"), ("registration", "Registration"), ("qualification", "Qualification"), ("facility_identity", "Facility identity"), ("facility_operation", "Facility operation"), ("other", "Other")]
    SOURCE_TYPES = [("manual_review", "Manual review"), ("official_registry", "Official registry"), ("provider_submission", "Provider submission"), ("facility_confirmation", "Facility confirmation"), ("other", "Other")]
    STATUSES = [("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected"), ("revoked", "Revoked")]
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, null=True, blank=True, related_name="verification_records")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, null=True, blank=True, related_name="verification_records")
    verification_type = models.CharField(max_length=32, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=16, choices=STATUSES, default="pending")
    source_type = models.CharField(max_length=24, choices=SOURCE_TYPES)
    evidence_reference = models.CharField(max_length=500, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_verifications")
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(doctor__isnull=False, hospital__isnull=True) | models.Q(doctor__isnull=True, hospital__isnull=False)), name="verification_one_owner"),
            models.CheckConstraint(condition=(~models.Q(status="verified") | (models.Q(evidence_reference__gt="") & models.Q(verified_by__isnull=False) & models.Q(verified_at__isnull=False))), name="verification_requires_evidence_reviewer_time"),
        ]
        indexes = [models.Index(fields=["doctor", "verification_type", "created_at"], name="verify_doc_type_date_idx"), models.Index(fields=["hospital", "verification_type", "created_at"], name="verify_hosp_type_date_idx")]

    def save(self, *args, **kwargs):
        # No dedicated MediReach reviewer permission exists yet. Keep verified
        # decisions disabled until an authorized creation service is approved.
        if self.status == "verified":
            raise ValidationError("Provider verification is disabled until reviewer permissions are configured.")
        return super().save(*args, **kwargs)


class ProviderContact(models.Model):
    CONTACT_TYPES = [("phone", "Phone"), ("email", "Email"), ("website", "Website"), ("fax", "Fax"), ("directory_route", "Directory route"), ("other", "Other")]
    VERIFICATION_STATUSES = [("unverified", "Unverified"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected"), ("revoked", "Revoked")]
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_contacts")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_contacts")
    contact_type = models.CharField(max_length=24, choices=CONTACT_TYPES)
    value = models.CharField(max_length=512)
    is_primary = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=16, choices=VERIFICATION_STATUSES, default="unverified")
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_contact_verifications")
    verification_evidence_reference = models.CharField(max_length=500, blank=True)
    source_record = models.ForeignKey(ProviderSourceRecord, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_contacts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(doctor__isnull=False, hospital__isnull=True) | models.Q(doctor__isnull=True, hospital__isnull=False)), name="provider_contact_one_owner"),
            models.CheckConstraint(condition=(~models.Q(verification_status="verified") | (models.Q(verified_at__isnull=False) & models.Q(verified_by__isnull=False) & models.Q(verification_evidence_reference__gt=""))), name="provider_contact_verified_has_evidence"),
            models.UniqueConstraint(fields=["doctor", "contact_type"], condition=models.Q(doctor__isnull=False, is_primary=True), name="doctor_primary_contact_type_uniq"),
            models.UniqueConstraint(fields=["hospital", "contact_type"], condition=models.Q(hospital__isnull=False, is_primary=True), name="hospital_primary_contact_type_uniq"),
        ]
        indexes = [models.Index(fields=["doctor", "contact_type", "verification_status"], name="contact_doc_type_status_idx"), models.Index(fields=["hospital", "contact_type", "verification_status"], name="contact_hosp_type_status_idx")]

    def clean(self):
        super().clean()
        if bool(self.doctor_id) == bool(self.hospital_id):
            raise ValidationError("A contact must belong to exactly one doctor or hospital.")
        if self.source_record_id:
            same_owner = (
                self.source_record.doctor_id == self.doctor_id
                if self.doctor_id
                else self.source_record.hospital_id == self.hospital_id
            )
            if not same_owner:
                raise ValidationError({"source_record": "Source record must belong to the same contact owner."})
