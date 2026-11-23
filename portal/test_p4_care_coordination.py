import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from portal.models import (
    Appointment, AppointmentSlot, AuditLog, Hospital, HospitalAdministrator,
    HospitalEnquiry, Referral, Doctor,
)


@override_settings(SECURE_SSL_REDIRECT=False)
class AppointmentRequestWorkflowTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("p4-patient", password="Safe-test-password-77")
        self.other = User.objects.create_user("p4-other", password="Safe-test-password-77")
        self.doctor = Doctor.objects.create(
            name="Dr Care Demo", specialization="Family Medicine", qualification="Demo qualification",
        )
        self.other_doctor = Doctor.objects.create(
            name="Dr Other Demo", specialization="Dermatology", qualification="Demo qualification",
        )
        self.slot = AppointmentSlot.objects.create(
            doctor=self.doctor, starts_at=timezone.now() + timedelta(days=3),
        )
        self.client.force_login(self.patient)

    def book(self, slot, doctor_id=None):
        return self.client.post(reverse("book_appointment", args=[slot.pk]), {
            "doctor_id": doctor_id if doctor_id is not None else slot.doctor_id,
        })

    def test_slot_must_belong_to_the_selected_doctor(self):
        response = self.client.post(
            reverse("book_appointment", args=[self.slot.pk]),
            {"doctor_id": self.other_doctor.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("appointments"))
        self.assertFalse(Appointment.objects.filter(slot=self.slot).exists())
        self.assertContains(response, "does not match the selected doctor")

    def test_slot_availability_and_duplicate_active_booking_are_enforced(self):
        self.book(self.slot)
        self.book(self.slot)
        self.assertEqual(Appointment.objects.filter(slot=self.slot, status="booked").count(), 1)
        taken = self.client.get(reverse("doctor_detail", args=[self.doctor.pk]))
        self.assertNotContains(taken, reverse("book_appointment", args=[self.slot.pk]))
        self.assertContains(self.client.get(reverse("appointments")), "not confirmed")

    def test_expired_and_prebooked_slots_are_unavailable(self):
        expired = AppointmentSlot.objects.create(
            doctor=self.other_doctor, starts_at=timezone.now() - timedelta(minutes=5),
        )
        unavailable = AppointmentSlot.objects.create(
            doctor=self.other_doctor, starts_at=timezone.now() + timedelta(days=4),
        )
        Appointment.objects.create(patient=self.other, slot=unavailable)
        self.book(expired)
        self.book(unavailable)
        self.assertFalse(Appointment.objects.filter(slot=expired).exists())
        self.assertEqual(Appointment.objects.filter(slot=unavailable, status="booked").count(), 1)

    def test_list_and_cancellation_are_limited_to_the_patient(self):
        own = Appointment.objects.create(patient=self.patient, slot=self.slot)
        other_slot = AppointmentSlot.objects.create(
            doctor=self.other_doctor, starts_at=timezone.now() + timedelta(days=5),
        )
        foreign = Appointment.objects.create(patient=self.other, slot=other_slot)
        page = self.client.get(reverse("appointments"))
        self.assertContains(page, "Dr Care Demo")
        self.assertNotContains(page, "Dr Other Demo")
        self.assertEqual(self.client.post(reverse("cancel_appointment", args=[foreign.pk])).status_code, 404)
        self.client.post(reverse("cancel_appointment", args=[own.pk]))
        own.refresh_from_db()
        self.assertEqual(own.status, "cancelled")


@override_settings(SECURE_SSL_REDIRECT=False)
class ReferralAndEnquiryWorkflowTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("p4-requester", password="Safe-test-password-77")
        self.other = User.objects.create_user("p4-private", password="Safe-test-password-77")
        self.admin = User.objects.create_user("p4-facility-admin", password="Safe-test-password-77")
        self.facility = Hospital.objects.create(name="Care Demo Facility", city="Pune", address="Demo address")
        self.other_facility = Hospital.objects.create(name="Other Demo Facility", city="Pune", address="Other address")
        self.client.force_login(self.patient)

    def test_referral_submission_preserves_selected_facility_and_status(self):
        page = self.client.get(reverse("referral_new"), {"hospital": self.facility.pk})
        self.assertContains(page, f'value="{self.facility.pk}" selected')
        response = self.client.post(reverse("referral_new"), {
            "hospital": self.facility.pk, "summary": "Please review my request for a specialist consultation.",
        }, follow=True)
        self.assertContains(response, "not been sent to the facility")
        referral = Referral.objects.get(patient=self.patient)
        self.assertEqual(referral.hospital, self.facility)
        self.assertEqual(referral.status, "received")

        referral.status = "reviewing"
        referral.save(update_fields=["status", "updated_at"])
        tracking = self.client.get(reverse("my_referrals"))
        self.assertContains(tracking, "Local status: Reviewing")
        self.assertContains(tracking, "Not confirmed by a provider")
        self.client.force_login(self.other)
        private_tracking = self.client.get(reverse("my_referrals"))
        self.assertNotContains(private_tracking, "Please review my request")
        self.assertNotContains(private_tracking, "Care Demo Facility")

    def test_referral_validation_and_api_reject_invalid_payloads(self):
        response = self.client.post(reverse("referral_new"), {"hospital": "999999", "summary": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Referral.objects.exists())
        invalid_shape = self.client.post(
            reverse("api_referrals"), data=json.dumps(["not", "an object"]), content_type="application/json",
        )
        self.assertEqual(invalid_shape.status_code, 400)

    def test_enquiry_submission_and_tracking_are_patient_private(self):
        response = self.client.post(reverse("hospital_enquiry"), {
            "hospital": self.facility.pk, "message": "Could you share the facility contact hours?",
        }, follow=True)
        self.assertContains(response, "saved to your account")
        self.assertContains(response, "not been sent to the hospital")
        enquiry = HospitalEnquiry.objects.get(patient=self.patient)
        self.assertEqual(enquiry.hospital, self.facility)
        self.assertContains(self.client.get(reverse("my_referrals")), "Could you share the facility contact hours?")
        self.client.force_login(self.other)
        page = self.client.get(reverse("my_referrals"))
        self.assertNotContains(page, "Could you share the facility contact hours?")

    def test_enquiry_validation_rejects_invalid_facility_or_empty_message(self):
        response = self.client.post(reverse("hospital_enquiry"), {"hospital": "999999", "message": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HospitalEnquiry.objects.exists())

    def test_hospital_admin_status_changes_are_audited_and_scoped(self):
        referral = Referral.objects.create(patient=self.patient, hospital=self.facility, summary="Request reason")
        enquiry = HospitalEnquiry.objects.create(patient=self.patient, hospital=self.facility, message="Question")
        HospitalAdministrator.objects.create(user=self.admin, hospital=self.facility)
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse("api_referral_status", args=[referral.pk]),
            data='{"status":"reviewing"}', content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(
            reverse("api_enquiry_status", args=[enquiry.pk]),
            data='{"status":"acknowledged"}', content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuditLog.objects.filter(hospital=self.facility).count(), 2)
        self.client.force_login(self.patient)
        tracking = self.client.get(reverse("my_referrals"))
        self.assertContains(tracking, "Local status: Reviewing")
        self.assertContains(tracking, "Local status: Acknowledged")
        self.assertContains(tracking, "do not confirm delivery")
        self.client.force_login(self.admin)
        foreign_referral = Referral.objects.create(patient=self.patient, hospital=self.other_facility, summary="Other")
        self.assertEqual(self.client.patch(
            reverse("api_referral_status", args=[foreign_referral.pk]),
            data='{"status":"closed"}', content_type="application/json",
        ).status_code, 404)


@override_settings(SECURE_SSL_REDIRECT=False)
class CareDashboardTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("p4-dashboard", password="Safe-test-password-77")
        self.client.force_login(self.patient)

    def test_empty_dashboard_has_request_empty_states(self):
        page = self.client.get(reverse("dashboard"))
        self.assertContains(page, "No appointment requests saved")
        self.assertContains(page, "No referral requests saved")
        self.assertContains(page, "No signed-in enquiries saved")

    def test_populated_dashboard_shows_owned_requests_and_next_steps(self):
        doctor = Doctor.objects.create(
            name="Dr Dashboard Demo", specialization="Family Medicine", qualification="Demo qualification",
        )
        slot = AppointmentSlot.objects.create(doctor=doctor, starts_at=timezone.now() + timedelta(days=2))
        Appointment.objects.create(patient=self.patient, slot=slot)
        facility = Hospital.objects.create(name="Dashboard Demo Facility", city="Pune", address="Demo address")
        Referral.objects.create(patient=self.patient, hospital=facility, summary="Referral reason")
        HospitalEnquiry.objects.create(patient=self.patient, hospital=facility, message="Enquiry reason")
        page = self.client.get(reverse("dashboard"))
        self.assertContains(page, "Dr Dashboard Demo")
        self.assertContains(page, "Dashboard Demo Facility")
        self.assertContains(page, "Next step: contact the provider directly")
        self.assertContains(page, "Referral reason")
        self.assertContains(page, "Enquiry reason")
