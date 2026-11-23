from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from portal.models import (
    AuditLog, ChatConversation, Doctor, EmergencyContact, Hospital,
    HospitalAdministrator, HospitalEnquiry, HospitalService, Referral,
)
from portal.services.chat import respond
from portal.services.first_aid import get_first_aid_guide
from portal.services.resources import generate_emergency_summary, search_hospitals


class MediReachServiceTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(
            name="Demo North", city="Pune", address="DEMO ONLY", latitude=18.52,
            longitude=73.85, is_demo=True,
        )
        self.service = HospitalService.objects.create(
            hospital=self.hospital, service_type="emergency", status="available",
            source="Demo only", expires_at=timezone.now() + timedelta(days=1),
        )

    def test_emergency_chat_returns_urgent_action(self):
        result, state = respond("I have severe chest pain")
        self.assertTrue(result["emergency"])
        self.assertEqual(result["emergency_number"], "112")
        self.assertEqual(state["stage"], "emergency")

    def test_severe_headache_with_neck_stiffness_escalates(self):
        result, _ = respond("I have a severe headache with neck stiffness")
        self.assertTrue(result["emergency"])
        self.assertIn("severe_headache_with_neck_stiffness", result["warning_signs"])

    def test_hospital_filter_and_expiring_status(self):
        self.assertEqual(len(search_hospitals(emergency=True)), 1)
        self.service.expires_at = timezone.now() - timedelta(seconds=1)
        self.service.save()
        self.assertEqual(self.service.effective_status, "unknown")
        self.assertEqual(search_hospitals(emergency=True), [])

    def test_hospital_search_location_and_distance(self):
        Hospital.objects.create(name="Demo Mumbai", city="Mumbai", address="DEMO ONLY", latitude=19.076, longitude=72.8777)
        # Distance is only meaningful when the search origin is explicit.
        results = search_hospitals(location="Pune", latitude=18.52, longitude=73.85)
        self.assertEqual(results[0]["name"], "Demo North")
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0]["distance_km"])

    def test_first_aid_source_and_review_date(self):
        guide = get_first_aid_guide("burns")
        self.assertTrue(guide["source_url"].startswith("https://"))
        self.assertTrue(guide["last_reviewed"])

    def test_emergency_summary_needs_location_consent(self):
        summary = generate_emergency_summary({"symptoms": "chest pain"}, latitude=18, longitude=73)
        self.assertFalse(summary["location_shared"])
        self.assertNotIn("Location shared by user", summary["reported_facts"])
        shared = generate_emergency_summary({"symptoms": "pain"}, True, 18, 73)
        self.assertTrue(shared["location_shared"])


@override_settings(SECURE_SSL_REDIRECT=False)
class MediReachAccessTests(TestCase):
    def setUp(self):
        self.client = Client(secure=True)
        self.client.defaults["wsgi.url_scheme"] = "https"
        self.patient = User.objects.create_user("patient", password="Strong-test-password-55")
        self.other = User.objects.create_user("other", password="Strong-test-password-55")
        self.hospital = Hospital.objects.create(name="Demo", city="Pune", address="Demo only")
        self.service = HospitalService.objects.create(hospital=self.hospital, service_type="icu")

    def test_emergency_page_and_first_aid_are_public(self):
        self.assertEqual(self.client.get(reverse("emergency")).status_code, 200)
        self.assertEqual(self.client.get(reverse("first_aid")).status_code, 200)
        self.assertEqual(self.client.get(reverse("hospitals")).status_code, 200)
        self.assertEqual(self.client.get(reverse("hospital_detail", args=[self.hospital.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("first_aid_detail", args=["burns"])).status_code, 200)

    def test_chat_page_and_emergency_summary_work(self):
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(reverse("chatbot")).status_code, 200)
        response = self.client.post(reverse("api_emergency_summary"), data={
            "reported_facts": {"symptoms": "headache", "onset": "since yesterday"}
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Symptoms reported", response.json()["reported_facts"])

    def test_patient_cannot_edit_hospital_service(self):
        self.client.force_login(self.patient)
        response = self.client.post(reverse("hospital_admin_service_update", args=[self.service.pk]), {
            "service_type": "icu", "status": "available", "source": "forged",
        })
        self.assertEqual(response.status_code, 403)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, "unknown")

    def test_hospital_admin_is_scoped_and_audited(self):
        HospitalAdministrator.objects.create(user=self.other, hospital=self.hospital)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("hospital_admin")).status_code, 200)
        response = self.client.post(reverse("hospital_admin_service_update", args=[self.service.pk]), {
            "service_type": "icu", "specialty_name": "", "status": "available",
            "source": "administrator report", "details": "", "expires_at": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AuditLog.objects.filter(administrator=self.other).count(), 1)
        self.service.refresh_from_db()
        self.assertEqual(self.service.updated_by, self.other)

    def test_patient_context_and_emergency_contacts_are_isolated(self):
        ChatConversation.objects.create(patient=self.patient, state={"symptoms": ["fever"]})
        ChatConversation.objects.create(patient=self.other, state={"symptoms": ["cough"]})
        EmergencyContact.objects.create(user=self.patient, name="A", phone="123")
        self.client.force_login(self.other)
        response = self.client.get(reverse("api_emergency_contacts"))
        self.assertEqual(response.json()["contacts"], [])

    def test_referral_submission_and_admin_status_tracking(self):
        self.client.force_login(self.patient)
        response = self.client.post(reverse("api_referrals"), data={
            "hospital": self.hospital.pk, "summary": "Patient requested information"
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        referral = Referral.objects.get(pk=response.json()["id"])
        self.assertEqual(referral.patient, self.patient)
        HospitalAdministrator.objects.create(user=self.other, hospital=self.hospital)
        self.client.force_login(self.other)
        response = self.client.patch(
            reverse("api_referral_status", args=[referral.pk]),
            data='{"status":"reviewing"}', content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        referral.refresh_from_db()
        self.assertEqual(referral.status, "reviewing")

