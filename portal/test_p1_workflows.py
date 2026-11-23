import json
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from portal.forms import HospitalProfileForm
from portal.models import (
    Appointment, AppointmentSlot, Doctor, EmergencyContact, Hospital,
    DoctorHospitalAffiliation, DoctorSpecialty, HospitalEnquiry, HospitalService,
    MedicalNote, ProviderContact, ProviderSourceRecord, Referral, Specialty,
)
from portal.services.chat import respond
from portal.services.resources import search_doctors, search_hospitals, serialize_hospital


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class DoctorDirectoryRepairTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("directory-patient", password="Strong-test-password-55")
        self.other = User.objects.create_user("directory-other", password="Strong-test-password-55")
        self.pune = Hospital.objects.create(
            name="Pune Demo Facility", city="Pune", address="Pune demo address", is_demo=True,
        )
        self.mumbai = Hospital.objects.create(
            name="Mumbai Directory Facility", city="Mumbai", address="Mumbai address", is_demo=False,
        )
        self.cardiologist = Doctor.objects.create(
            name="Dr Anika Rao", specialization="Cardiology", experience=8,
            qualification="Demo qualification", bio="Stored profile bio", hospital=self.pune,
            verification_status="demo",
        )
        self.pediatrician = Doctor.objects.create(
            name="Dr Dev Shah", specialization="Pediatrics", experience=4,
            qualification="MBBS", hospital=self.pune,
        )
        self.other_city_cardiologist = Doctor.objects.create(
            name="Cardio Specialist", specialization="Cardiology", experience=6,
            qualification="MD", hospital=self.mumbai,
        )

    def test_web_search_combines_keyword_specialty_and_city_and_links_real_record(self):
        response = self.client.get(reverse("doctors"), {
            "q": "Dr", "specialty": "Cardiology", "location": "Pune",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dr Anika Rao")
        self.assertContains(response, reverse("doctor_detail", args=[self.cardiologist.pk]))
        self.assertNotContains(response, "Dr Dev Shah")
        self.assertNotContains(response, "Cardio Specialist")
        self.assertContains(response, "DEMO — fictional profile")

    def test_doctor_api_combines_filters_and_returns_stored_profile_data(self):
        response = self.client.get(reverse("api_doctors"), {
            "q": "Cardio", "specialty": "Cardiology", "location": "Pune",
        })
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([item["id"] for item in results], [self.cardiologist.pk])
        self.assertEqual(results[0]["name"], "Dr Anika Rao")
        self.assertEqual(results[0]["verification_status"], "demo")
        self.assertEqual(self.client.post(reverse("api_doctors")).status_code, 405)

    def test_doctor_detail_only_shows_future_unbooked_local_slots(self):
        open_slot = AppointmentSlot.objects.create(
            doctor=self.cardiologist, starts_at=timezone.now() + timedelta(days=3),
        )
        booked_slot = AppointmentSlot.objects.create(
            doctor=self.cardiologist, starts_at=timezone.now() + timedelta(days=4),
        )
        AppointmentSlot.objects.create(doctor=self.cardiologist, starts_at=timezone.now() - timedelta(days=1))
        Appointment.objects.create(patient=self.other, slot=booked_slot)
        self.client.force_login(self.patient)
        response = self.client.get(reverse("doctor_detail", args=[self.cardiologist.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("book_appointment", args=[open_slot.pk]))
        self.assertNotContains(response, reverse("book_appointment", args=[booked_slot.pk]))
        self.assertContains(response, "DEMO profile")
        self.assertContains(response, "no provider is contacted")

    def test_doctor_search_has_actionable_empty_state(self):
        response = self.client.get(reverse("doctors"), {"q": "Neurology"})
        self.assertContains(response, "No doctors matched those filters")
        self.assertContains(response, reverse("doctors"))

    def test_doctor_queryset_and_api_match_the_same_record_set(self):
        expected = list(search_doctors(specialty="Cardiology", location="Pune"))
        self.assertEqual([row["id"] for row in expected], [self.cardiologist.pk])

    def test_current_affiliations_replace_legacy_display_and_historical_links_are_not_current(self):
        DoctorHospitalAffiliation.objects.create(
            doctor=self.cardiologist, hospital=self.pune, is_current=False,
            valid_until=timezone.localdate() - timedelta(days=1),
        )
        DoctorHospitalAffiliation.objects.create(
            doctor=self.cardiologist, hospital=self.mumbai, is_current=True, is_primary=True,
        )
        result = next(item for item in search_doctors(query="Anika") if item["id"] == self.cardiologist.pk)
        self.assertEqual([item["id"] for item in result["facilities"]], [self.mumbai.pk])
        self.assertEqual(result["hospital"], self.mumbai.name)
        self.assertNotIn(self.cardiologist.pk, [item["id"] for item in search_doctors(location="Pune")])
        self.assertIn(self.cardiologist.pk, [item["id"] for item in search_doctors(location="Mumbai")])

    def test_structured_specialties_are_deduplicated_and_searchable(self):
        specialty = Specialty.objects.create(name="Cardiology", slug="cardiology")
        DoctorSpecialty.objects.create(doctor=self.cardiologist, specialty=specialty, is_primary=True)
        result = next(item for item in search_doctors(query="Anika") if item["id"] == self.cardiologist.pk)
        self.assertEqual(result["specialties"], ["Cardiology"])
        self.assertEqual(len(search_doctors(specialty="cardiology")), 2)

    def test_legacy_verified_label_and_imported_source_do_not_create_verification(self):
        self.cardiologist.verification_status = "verified"
        self.cardiologist.save(update_fields=["verification_status"])
        ProviderSourceRecord.objects.create(
            doctor=self.cardiologist, source_type="imported", source_name="Example registry",
            external_id="sample-1", source_url="javascript:alert(1)",
        )
        result = next(item for item in search_doctors(query="Anika") if item["id"] == self.cardiologist.pk)
        self.assertEqual(result["provider_status"], "unverified")
        self.assertEqual(result["trust_label"], "Unverified — no current verification record")
        self.assertEqual(result["sources"][0]["source_name"], "Example registry")
        self.assertIsNone(result["sources"][0]["source_url"])

    def test_unverified_doctor_contact_is_not_serialized_as_a_verified_contact(self):
        ProviderContact.objects.create(
            doctor=self.pediatrician, contact_type="phone", value="UNVERIFIED EXAMPLE",
            verification_status="unverified",
        )
        result = next(item for item in search_doctors(query="Dev Shah"))
        self.assertEqual(result["contacts"], [])

    def test_demo_doctor_credentials_are_not_presented_as_real_credentials(self):
        result = next(item for item in search_doctors(query="Anika Rao"))
        self.assertEqual(result["provider_status"], "demo")
        self.assertIsNone(result["qualification"])
        self.assertIsNone(result["registration_number"])


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class HospitalDirectoryRepairTests(TestCase):
    def setUp(self):
        self.demo = Hospital.objects.create(
            name="North Demo Hospital", city="Pune", address="North demo address",
            latitude=18.5204, longitude=73.8567, is_demo=True,
        )
        self.real_record = Hospital.objects.create(
            name="South Directory Record", city="Mumbai", address="Pune Road, Mumbai",
            latitude=19.076, longitude=72.8777, is_demo=False, verification_status="confirmed",
        )
        HospitalService.objects.create(
            hospital=self.demo, service_type="emergency", specialty_name="",
            status="unknown", source="Demo source",
        )
        HospitalService.objects.create(
            hospital=self.demo, service_type="emergency", specialty_name="Night",
            status="available", source="Demo source",
        )

    def test_hospital_keyword_and_location_filters_are_both_applied(self):
        results = search_hospitals(query="North Demo", location="Mumbai")
        self.assertEqual(results, [])
        results = search_hospitals(query="North Demo", location="Pune")
        self.assertEqual([item["id"] for item in results], [self.demo.pk])

    def test_service_filter_checks_all_matching_reports_and_labels_demo_status(self):
        results = search_hospitals(emergency=True)
        self.assertEqual([item["id"] for item in results], [self.demo.pk])
        service = results[0]["services"][0]
        self.assertIn(service["status"], {"unknown", "available"})
        self.assertTrue(service["is_demo"])
        self.assertIn("Demo status:", service["status_label"])
        self.assertNotIn("confirmed live", service["status_label"].lower())

    def test_hospital_coordinates_are_suppressed_when_out_of_range(self):
        invalid = Hospital.objects.create(
            name="Invalid Coordinate Record", city="Test", address="Stored record",
            latitude=91, longitude=181,
        )
        result = next(item for item in search_hospitals(latitude=18, longitude=73) if item["id"] == invalid.pk)
        self.assertIsNone(result["latitude"])
        self.assertIsNone(result["longitude"])
        self.assertIsNone(result["distance_km"])
        api_response = self.client.get(reverse("api_hospital_detail", args=[invalid.pk]))
        self.assertEqual(api_response.status_code, 200)
        self.assertIsNone(api_response.json()["latitude"])

    def test_hospital_profile_form_rejects_invalid_coordinates(self):
        form = HospitalProfileForm({
            "name": "Test", "city": "Test", "address": "Test",
            "latitude": "90.1", "longitude": "181",
        }, instance=self.demo)
        self.assertFalse(form.is_valid())
        self.assertIn("latitude", form.errors)
        self.assertIn("longitude", form.errors)

    def test_map_and_api_pages_render_data_and_keep_list_fallback(self):
        page = self.client.get(reverse("hospitals"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "id=\"map\"")
        self.assertContains(page, "The directory list remains available if the map does not load")
        self.assertContains(page, "Map tiles by OpenStreetMap contributors")
        self.assertContains(page, "hospital-finder.js")
        api = self.client.get(reverse("api_hospitals"))
        self.assertEqual(api.status_code, 200)
        self.assertIn("results", api.json())
        map_script = (Path(__file__).resolve().parent.parent / "static/portal/hospital-finder.js").read_text()
        self.assertIn("else if (!window.L) {", map_script)
        self.assertIn("Map library: failed to load.", map_script)
        self.assertIn("if (osmForm && osmButton && osmResults)", map_script)
        self.assertIn("tiles.on('tileerror'", map_script)
        self.assertIn("latitude < -90 || latitude > 90", map_script)
        self.assertIn("https://tile.openstreetmap.org/{z}/{x}/{y}.png", map_script)
        self.assertIn("referrerPolicy: 'strict-origin-when-cross-origin'", map_script)
        self.assertIn("&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors", map_script)

    def test_facility_detail_uses_stored_fields_and_preserves_enquiry_selection(self):
        detail = self.client.get(reverse("hospital_detail", args=[self.demo.pk]))
        self.assertContains(detail, "North Demo Hospital")
        self.assertContains(detail, "DEMO")
        self.assertContains(detail, "Demo status:")
        self.assertContains(detail, "not confirmed live capacity")
        self.assertContains(detail, f"?hospital={self.demo.pk}")
        form_page = self.client.get(reverse("hospital_enquiry"), {"hospital": self.demo.pk})
        self.assertEqual(form_page.status_code, 200)
        self.assertContains(form_page, f'value="{self.demo.pk}" selected')

    def test_unverified_hospital_contact_is_labelled_and_rejected_contact_is_hidden(self):
        facility = Hospital.objects.create(
            name="Contact Example Facility", city="Pune", address="Example only",
            phone="+91 98765 43210", is_demo=False, verification_status="confirmed",
        )
        contact = ProviderContact.objects.create(
            hospital=facility, contact_type="phone", value=facility.phone,
            verification_status="unverified",
        )
        data = serialize_hospital(facility)
        self.assertEqual(data["phone"], facility.phone)
        self.assertEqual(data["phone_contact_label"], "Unverified contact information")
        self.assertNotIn("not-a-real-number", [item["value"] for item in data["contacts"] if item["verification_status"] == "verified"])
        contact.verification_status = "rejected"
        contact.save(update_fields=["verification_status"])
        self.assertIsNone(serialize_hospital(facility)["phone"])

    def test_malformed_stored_phone_and_unsafe_website_are_never_exposed_as_actions(self):
        facility = Hospital.objects.create(
            name="Unsafe Contact Example", city="Pune", address="Example only",
            phone="javascript:alert(1)", website="javascript:alert(1)",
            is_demo=False, verification_status="verified",
        )
        data = serialize_hospital(facility)
        self.assertIsNone(data["phone"])
        self.assertIsNone(data["website"])


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class AppointmentRepairTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("booking-patient", password="Strong-test-password-55")
        self.other = User.objects.create_user("booking-other", password="Strong-test-password-55")
        self.doctor = Doctor.objects.create(
            name="Dr Demo", specialization="Family Medicine", experience=5,
            qualification="Demo qualification", verification_status="demo",
        )
        self.slot = AppointmentSlot.objects.create(
            doctor=self.doctor, starts_at=timezone.now() + timedelta(days=2),
        )
        self.client.force_login(self.patient)

    def test_booking_is_local_and_duplicate_active_booking_is_rejected(self):
        response = self.client.post(reverse("book_appointment", args=[self.slot.pk]), {"doctor_id": self.doctor.pk})
        self.assertRedirects(response, reverse("appointments"))
        self.assertEqual(Appointment.objects.filter(slot=self.slot, status="booked").count(), 1)
        self.assertContains(self.client.get(reverse("appointments")), "not confirmed by a provider")
        self.assertContains(self.client.get(reverse("appointments")), "local")
        self.client.post(reverse("book_appointment", args=[self.slot.pk]), {"doctor_id": self.doctor.pk})
        self.assertEqual(Appointment.objects.filter(slot=self.slot, status="booked").count(), 1)

    def test_expired_slot_cannot_be_booked_or_cancelled(self):
        expired = AppointmentSlot.objects.create(
            doctor=self.doctor, starts_at=timezone.now() - timedelta(minutes=1),
        )
        self.client.post(reverse("book_appointment", args=[expired.pk]), {"doctor_id": self.doctor.pk})
        self.assertFalse(Appointment.objects.filter(slot=expired).exists())
        appointment = Appointment.objects.create(patient=self.patient, slot=expired)
        response = self.client.post(reverse("cancel_appointment", args=[appointment.pk]))
        self.assertRedirects(response, reverse("appointments"))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "booked")

    def test_appointment_list_and_cancellation_are_patient_scoped(self):
        own = Appointment.objects.create(patient=self.patient, slot=self.slot)
        other_doctor = Doctor.objects.create(
            name="Other Patient Doctor", specialization="Dermatology", experience=3,
            qualification="MBBS", verification_status="demo",
        )
        other_slot = AppointmentSlot.objects.create(
            doctor=other_doctor, starts_at=timezone.now() + timedelta(days=3),
        )
        other = Appointment.objects.create(patient=self.other, slot=other_slot)
        page = self.client.get(reverse("appointments"))
        self.assertContains(page, "Cancel local booking")
        self.assertNotContains(page, "Other Patient Doctor")
        self.assertEqual(self.client.post(reverse("cancel_appointment", args=[other.pk])).status_code, 404)
        self.client.post(reverse("cancel_appointment", args=[own.pk]))
        own.refresh_from_db()
        self.assertEqual(own.status, "cancelled")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class EnquiryAndPatientExperienceRepairTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("experience-patient", password="Strong-test-password-55")
        self.other = User.objects.create_user("experience-other", password="Strong-test-password-55")
        self.hospital = Hospital.objects.create(name="Demo Facility", city="Pune", address="Demo only")

    def test_referral_and_general_enquiry_have_distinct_chat_actions(self):
        referral, _ = respond("I need a referral")
        enquiry, _ = respond("I want to make a hospital enquiry")
        self.assertEqual(referral["response_type"], "referral_action")
        self.assertEqual(referral["actions"][0]["href"], "/referrals/new/")
        self.assertEqual(enquiry["response_type"], "enquiry_action")
        self.assertEqual(enquiry["actions"][0]["href"], "/enquiries/new/")

    def test_authenticated_enquiry_is_saved_and_trackable_but_not_delivered(self):
        self.client.force_login(self.patient)
        response = self.client.post(reverse("hospital_enquiry"), {
            "hospital": self.hospital.pk, "message": "Please share visiting hours.",
        }, follow=True)
        self.assertContains(response, "saved to your account")
        self.assertContains(response, "not been sent to the hospital")
        enquiry = HospitalEnquiry.objects.get()
        self.assertEqual(enquiry.patient, self.patient)
        tracking = self.client.get(reverse("my_referrals"))
        self.assertContains(tracking, "General enquiries")
        self.assertContains(tracking, "Please share visiting hours.")

    def test_anonymous_enquiry_is_saved_without_patient_tracking(self):
        response = self.client.post(reverse("hospital_enquiry"), {
            "hospital": self.hospital.pk, "message": "Anonymous question.",
        }, follow=True)
        self.assertContains(response, "cannot be tracked from an account")
        enquiry = HospitalEnquiry.objects.get()
        self.assertIsNone(enquiry.patient)
        self.assertEqual(self.client.get(reverse("my_referrals")).status_code, 302)

    def test_contact_can_be_created_edited_and_deleted_only_by_owner(self):
        self.client.force_login(self.patient)
        response = self.client.post(reverse("emergency_profile"), {
            "name": "Asha", "phone": "+91 1234567890", "relationship": "Sibling",
        })
        self.assertRedirects(response, reverse("emergency_profile"))
        contact = EmergencyContact.objects.get(user=self.patient)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("edit_emergency_contact", args=[contact.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("delete_emergency_contact", args=[contact.pk])).status_code, 404)
        self.client.force_login(self.patient)
        response = self.client.post(reverse("edit_emergency_contact", args=[contact.pk]), {
            "name": "Asha Rao", "phone": "+91 9999999999", "relationship": "Sister",
        })
        self.assertRedirects(response, reverse("emergency_profile"))
        contact.refresh_from_db()
        self.assertEqual(contact.name, "Asha Rao")
        self.assertEqual(contact.phone, "+91 9999999999")
        response = self.client.post(reverse("delete_emergency_contact", args=[contact.pk]))
        self.assertRedirects(response, reverse("emergency_profile"))
        self.assertFalse(EmergencyContact.objects.filter(pk=contact.pk).exists())

    def test_dashboard_and_sidebar_link_to_requests_and_core_patient_pages(self):
        self.client.force_login(self.patient)
        page = self.client.get(reverse("dashboard"))
        self.assertContains(page, reverse("doctors"))
        self.assertContains(page, reverse("appointments"))
        self.assertContains(page, reverse("my_referrals"))
        self.assertContains(page, "My Requests")

    def test_note_validation_and_history_conversation_navigation_keep_owner_scope(self):
        self.client.force_login(self.patient)
        invalid_note = self.client.post(reverse("notes"), {"title": "", "body": ""})
        self.assertEqual(invalid_note.status_code, 200)
        self.assertFalse(MedicalNote.objects.filter(patient=self.patient).exists())
        own_conversation = self.patient.chat_conversations.create()
        other_conversation = self.other.chat_conversations.create()
        self.patient.chat_messages.create(
            conversation=own_conversation, role="user", content="My own message",
        )
        self.patient.chat_messages.create(
            conversation=other_conversation, role="user", content="Inconsistent foreign conversation",
        )
        history = self.client.get(reverse("chat_history"))
        self.assertContains(history, reverse("chatbot") + f"?conversation={own_conversation.pk}")
        self.assertNotContains(history, reverse("chatbot") + f"?conversation={other_conversation.pk}")
        self.assertContains(history, "Inconsistent foreign conversation")

