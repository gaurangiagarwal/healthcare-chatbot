import ast
import json
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from portal.models import (
    ChatConversation, Doctor, Hospital, HospitalAdministrator, HospitalEnquiry, Referral,
)
from portal.chatbot import process_message
from portal.services.resources import serialize_doctor
from portal.services.ollama import _configuration


ROOT = Path(__file__).resolve().parent.parent


class ProviderContactRouteSafetyTests(SimpleTestCase):
    def serialize_route(self, route):
        doctor = Doctor(
            name="Example clinician",
            specialization="Family Medicine",
            qualification="Not supplied",
            contact_route=route,
        )
        doctor._provider_sources = []
        doctor._provider_verifications = []
        doctor._provider_contacts = []
        doctor._provider_affiliations = []
        doctor._structured_specialties = []
        return serialize_doctor(doctor)["contact_route"]

    def test_only_same_site_paths_and_credential_free_https_routes_are_exposed(self):
        self.assertEqual(self.serialize_route("/hospitals/12/"), "/hospitals/12/")
        self.assertEqual(self.serialize_route("http://clinic.example/contact"), "http://clinic.example/contact")
        self.assertEqual(self.serialize_route("https://clinic.example/contact"), "https://clinic.example/contact")
        for unsafe in (
            "javascript:alert(1)",
            "//attacker.example/contact",
            "ftp://clinic.example/contact",
            "https://user:password@clinic.example/contact",
        ):
            with self.subTest(route=unsafe):
                self.assertIsNone(self.serialize_route(unsafe))


@override_settings(SECURE_SSL_REDIRECT=False)
class ChatCoordinateValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("p6-chat-user", password="Safe-test-password-77")
        self.client.force_login(self.user)

    def test_invalid_optional_coordinates_return_400_without_creating_a_conversation(self):
        invalid_coordinates = (
            {"latitude": 18.5},
            {"latitude": True, "longitude": 73.8},
            {"latitude": 91, "longitude": 73.8},
            {"latitude": 18.5, "longitude": float("inf")},
        )
        for coordinates in invalid_coordinates:
            with self.subTest(coordinates=coordinates):
                response = self.client.post(
                    reverse("chat_send"),
                    data=json.dumps({"message": "Find hospitals", **coordinates}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
        self.assertFalse(ChatConversation.objects.filter(patient=self.user).exists())


class MigrationSourceIntegrityTests(SimpleTestCase):
    def test_provider_foundation_migration_is_valid_python_source(self):
        migration = ROOT / "portal" / "migrations" / "0004_provider_data_foundation.py"
        ast.parse(migration.read_text(encoding="utf-8"), filename=str(migration))


class ChatbotBrandingTests(SimpleTestCase):
    def test_legacy_doctor_contact_reply_uses_the_current_product_name(self):
        reply, _ = process_message("What is the doctor's phone number?")
        self.assertIn("MediReach", reply)
        self.assertNotIn("CareBridge", reply)


@override_settings(SECURE_SSL_REDIRECT=False)
class ProviderDiscoveryRequestShapeTests(SimpleTestCase):
    def test_invalid_filter_types_return_400_without_calling_discovery(self):
        invalid_payloads = (
            {"query": {"unexpected": "object"}},
            {"result_types": [{"unexpected": "object"}]},
            {"include_osm": "true"},
        )
        with patch("portal.views.discover_providers") as discover:
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    response = self.client.post(
                        reverse("api_provider_discovery"),
                        data=json.dumps(payload),
                        content_type="application/json",
                    )
                    self.assertEqual(response.status_code, 400)
            discover.assert_not_called()


class OllamaEndpointBoundaryTests(SimpleTestCase):
    def test_optional_model_configuration_accepts_loopback_only(self):
        base_values = {"OLLAMA_MODEL": "local-model", "OLLAMA_TIMEOUT_SECONDS": "8"}
        with patch.dict(os.environ, {**base_values, "OLLAMA_BASE_URL": "http://127.0.0.1:11434"}):
            self.assertIsNotNone(_configuration())
        with patch.dict(os.environ, {**base_values, "OLLAMA_BASE_URL": "http://[::1]:11434"}):
            self.assertIsNotNone(_configuration())
        with patch.dict(os.environ, {**base_values, "OLLAMA_BASE_URL": "https://ollama.example"}):
            self.assertIsNone(_configuration())


@override_settings(SECURE_SSL_REDIRECT=False)
class FacilityStatusRequestShapeTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("p6-facility-admin", password="Safe-test-password-77")
        self.hospital = Hospital.objects.create(
            name="P6 demo facility", city="Pune", address="Demo address",
        )
        HospitalAdministrator.objects.create(user=self.admin, hospital=self.hospital)
        self.referral = Referral.objects.create(hospital=self.hospital, summary="Demo request")
        self.enquiry = HospitalEnquiry.objects.create(hospital=self.hospital, message="Demo enquiry")
        self.client.force_login(self.admin)

    def test_non_string_status_values_return_400_without_changes(self):
        endpoints = (
            reverse("api_referral_status", args=[self.referral.pk]),
            reverse("api_enquiry_status", args=[self.enquiry.pk]),
        )
        for endpoint in endpoints:
            for status in ([], {"unexpected": "object"}):
                with self.subTest(endpoint=endpoint, status=status):
                    response = self.client.patch(
                        endpoint,
                        data=json.dumps({"status": status}),
                        content_type="application/json",
                    )
                    self.assertEqual(response.status_code, 400)
        self.referral.refresh_from_db()
        self.enquiry.refresh_from_db()
        self.assertEqual(self.referral.status, "received")
        self.assertEqual(self.enquiry.status, "received")

