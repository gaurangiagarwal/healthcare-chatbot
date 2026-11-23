import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0003_hospital_doctor_contact_route_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Specialty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
                "indexes": [models.Index(fields=["is_active", "name"], name="specialty_active_name_idx")],
            },
        ),
        migrations.AddField(
            model_name="doctor",
            name="registration_number",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="doctor",
            name="professional_status",
            field=models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("unknown", "Unknown")], default="unknown", max_length=12),
        ),
        migrations.AddField(
            model_name="hospital",
            name="facility_type",
            field=models.CharField(blank=True, choices=[("hospital", "Hospital"), ("clinic", "Clinic"), ("diagnostic_centre", "Diagnostic centre"), ("imaging_centre", "Imaging centre"), ("pharmacy", "Pharmacy"), ("other", "Other")], default=None, max_length=24, null=True),
        ),
        migrations.AddField(
            model_name="hospital",
            name="operational_status",
            field=models.CharField(choices=[("operational", "Operational"), ("temporarily_closed", "Temporarily closed"), ("permanently_closed", "Permanently closed"), ("unknown", "Unknown")], default="unknown", max_length=24),
        ),
        migrations.CreateModel(
            name="ProviderSourceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("imported", "Imported"), ("provider_submission", "Provider submission"), ("manual_entry", "Manual entry"), ("demo_data", "Demo data"), ("legacy_unattributed", "Legacy unattributed"), ("other", "Other")], max_length=24)),
                ("external_id", models.CharField(blank=True, default="", max_length=255)),
                ("source_name", models.CharField(max_length=120)),
                ("source_url", models.URLField(blank=True)),
                ("retrieved_at", models.DateTimeField(blank=True, null=True)),
                ("source_updated_at", models.DateTimeField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("doctor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_records", to="portal.doctor")),
                ("hospital", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_records", to="portal.hospital")),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="provider_source_submissions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=(models.Q(("doctor__isnull", False), ("hospital__isnull", True)) | models.Q(("doctor__isnull", True), ("hospital__isnull", False))), name="provider_source_one_owner"),
                    models.UniqueConstraint(condition=models.Q(("external_id", ""), _negated=True), fields=("source_type", "source_name", "external_id"), name="prov_src_external_id_uniq"),
                ],
                "indexes": [models.Index(fields=["doctor", "source_type"], name="provsource_doc_type_idx"), models.Index(fields=["hospital", "source_type"], name="provsource_hosp_type_idx")],
            },
        ),
        migrations.CreateModel(
            name="DoctorSpecialty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="specialty_links", to="portal.doctor")),
                ("source_record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="doctor_specialty_links", to="portal.providersourcerecord")),
                ("specialty", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="doctor_links", to="portal.specialty")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("doctor", "specialty"), name="doctor_specialty_uniq"), models.UniqueConstraint(condition=models.Q(("is_primary", True)), fields=("doctor",), name="doctor_one_primary_specialty")],
                "indexes": [models.Index(fields=["specialty", "doctor"], name="docspecialty_spec_doc_idx")],
            },
        ),
        migrations.CreateModel(
            name="DoctorHospitalAffiliation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relationship_type", models.CharField(choices=[("employed", "Employed"), ("visiting", "Visiting"), ("consulting", "Consulting"), ("other", "Other"), ("unknown", "Unknown")], default="unknown", max_length=24)),
                ("is_primary", models.BooleanField(default=False)),
                ("is_current", models.BooleanField(default=True)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="affiliations", to="portal.doctor")),
                ("hospital", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="doctor_affiliations", to="portal.hospital")),
                ("source_record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="affiliations", to="portal.providersourcerecord")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("is_current", True)), fields=("doctor", "hospital"), name="doctor_current_facility_uniq"),
                    models.UniqueConstraint(condition=models.Q(("is_current", True), ("is_primary", True)), fields=("doctor",), name="doctor_one_current_primary_facility"),
                    models.CheckConstraint(condition=(models.Q(("valid_from__isnull", True)) | models.Q(("valid_until__isnull", True)) | models.Q(("valid_until__gte", models.F("valid_from")))), name="doctor_affiliation_valid_dates"),
                ],
                "indexes": [models.Index(fields=["doctor", "is_current"], name="affiliation_doc_current_idx"), models.Index(fields=["hospital", "is_current"], name="affiliation_hosp_current_idx")],
            },
        ),
        migrations.CreateModel(
            name="ProviderVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("verification_type", models.CharField(choices=[("identity", "Identity"), ("registration", "Registration"), ("qualification", "Qualification"), ("facility_identity", "Facility identity"), ("facility_operation", "Facility operation"), ("other", "Other")], max_length=32)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected"), ("revoked", "Revoked")], default="pending", max_length=16)),
                ("source_type", models.CharField(choices=[("manual_review", "Manual review"), ("official_registry", "Official registry"), ("provider_submission", "Provider submission"), ("facility_confirmation", "Facility confirmation"), ("other", "Other")], max_length=24)),
                ("evidence_reference", models.CharField(blank=True, max_length=500)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("doctor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="verification_records", to="portal.doctor")),
                ("hospital", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="verification_records", to="portal.hospital")),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="provider_verifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=(models.Q(("doctor__isnull", False), ("hospital__isnull", True)) | models.Q(("doctor__isnull", True), ("hospital__isnull", False))), name="verification_one_owner"),
                    models.CheckConstraint(condition=(models.Q(("status", "verified"), _negated=True) | (models.Q(("evidence_reference__gt", "")) & models.Q(("verified_by__isnull", False)) & models.Q(("verified_at__isnull", False)))), name="verification_requires_evidence_reviewer_time"),
                ],
                "indexes": [models.Index(fields=["doctor", "verification_type", "created_at"], name="verify_doc_type_date_idx"), models.Index(fields=["hospital", "verification_type", "created_at"], name="verify_hosp_type_date_idx")],
            },
        ),
        migrations.CreateModel(
            name="ProviderContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contact_type", models.CharField(choices=[("phone", "Phone"), ("email", "Email"), ("website", "Website"), ("fax", "Fax"), ("directory_route", "Directory route"), ("other", "Other")], max_length=24)),
                ("value", models.CharField(max_length=512)),
                ("is_primary", models.BooleanField(default=False)),
                ("verification_status", models.CharField(choices=[("unverified", "Unverified"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected"), ("revoked", "Revoked")], default="unverified", max_length=16)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("verification_evidence_reference", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("doctor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="provider_contacts", to="portal.doctor")),
                ("hospital", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="provider_contacts", to="portal.hospital")),
                ("source_record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="provider_contacts", to="portal.providersourcerecord")),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="provider_contact_verifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=(models.Q(("doctor__isnull", False), ("hospital__isnull", True)) | models.Q(("doctor__isnull", True), ("hospital__isnull", False))), name="provider_contact_one_owner"),
                    models.CheckConstraint(condition=(models.Q(("verification_status", "verified"), _negated=True) | (models.Q(("verified_at__isnull", False)) & models.Q(("verified_by__isnull", False)) & models.Q(("verification_evidence_reference__gt", "")))), name="provider_contact_verified_has_evidence"),
                    models.UniqueConstraint(condition=models.Q(("doctor__isnull", False), ("is_primary", True)), fields=("doctor", "contact_type"), name="doctor_primary_contact_type_uniq"),
                    models.UniqueConstraint(condition=models.Q(("hospital__isnull", False), ("is_primary", True)), fields=("hospital", "contact_type"), name="hospital_primary_contact_type_uniq"),
                ],
                "indexes": [models.Index(fields=["doctor", "contact_type", "verification_status"], name="contact_doc_type_status_idx"), models.Index(fields=["hospital", "contact_type", "verification_status"], name="contact_hosp_type_status_idx")],
            },
        ),
        migrations.AddField(model_name="doctor", name="specialties", field=models.ManyToManyField(blank=True, related_name="doctors", through="portal.DoctorSpecialty", to="portal.specialty")),
        migrations.AddField(model_name="doctor", name="facilities", field=models.ManyToManyField(blank=True, related_name="affiliated_doctors", through="portal.DoctorHospitalAffiliation", to="portal.hospital")),
    ]
