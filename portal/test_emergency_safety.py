import json
import re
from pathlib import Path

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from portal.models import EmergencyCase
from portal.services.chat import respond
from portal.services.safety import assess_emergency


class EmergencyScreeningTests(TestCase):
    def test_supported_warning_signs(self):
        examples = {
            "chest_pain": "I have severe chest pain",
            "breathing_difficulty": "I am struggling to breathe",
            "stroke_warning": "My father's face is drooping and his speech is slurred",
            "severe_bleeding": "The bleeding will not stop",
            "seizure": "She is having a seizure now",
            "severe_allergic_reaction": "My throat is swelling after an allergic reaction",
            "unconsciousness": "He is unconscious",
            "sudden_severe_headache": "I have a sudden, extremely severe headache",
            "severe_headache_with_neck_stiffness": "I have a severe headache with neck stiffness",
            "severe_confusion": "My mother suddenly became confused",
            "suicidal_crisis": "I feel suicidal",
        }
        for warning, message in examples.items():
            with self.subTest(warning=warning):
                result = assess_emergency(message)
                self.assertTrue(result["is_emergency"])
                self.assertIn(warning, result["matched_warning_signs"])
                self.assertEqual(result["emergency_number"], "112")
                self.assertEqual(result["urgency_level"], "emergency")

    def test_multiple_signs_are_all_reported(self):
        result = assess_emergency("My mother has chest pressure and is struggling to breathe")
        self.assertEqual(result["matched_warning_signs"], ["chest_pain", "breathing_difficulty"])

    def test_natural_language_variants_are_recognized(self):
        for message in (
            "He cannot catch his breath",
            "There is lots of bleeding from the wound",
            "She passed out and will not wake",
            "Her tongue is swelling after an allergy",
            "I have the worst headache of my life",
        ):
            with self.subTest(message=message):
                self.assertTrue(assess_emergency(message)["is_emergency"])

    def test_negated_historical_hypothetical_and_educational_mentions_do_not_escalate(self):
        for message in (
            "I do not have chest pain",
            "No difficulty breathing",
            "I had chest pain last week",
            "My old seizure history is in my chart",
            "What if someone is having a stroke?",
            "How do you recognize a stroke?",
            "What is a stroke?",
            "What is a seizure?",
            "What are stroke symptoms?",
            "Could this be anaphylaxis?",
        ):
            with self.subTest(message=message):
                self.assertFalse(assess_emergency(message)["is_emergency"])

    def test_another_persons_current_symptom_is_escalated(self):
        result = assess_emergency("My friend is unconscious and not waking up")
        self.assertTrue(result["is_emergency"])

    def test_current_recurrence_after_a_historical_symptom_is_escalated(self):
        result = assess_emergency("I had chest pain last week, but the chest pain is back now")
        self.assertTrue(result["is_emergency"])

    def test_explicit_current_symptom_overrides_hypothetical_framing(self):
        result, _ = respond("What if I have severe chest pain right now?")
        self.assertEqual(result["response_type"], "emergency_alert")
        self.assertIn("chest_pain", result["warning_signs"])
        third_party, _ = respond("What if someone is having a stroke right now?")
        self.assertEqual(third_party["response_type"], "emergency_alert")

    def test_recent_stroke_is_not_suppressed_as_history(self):
        result, _ = respond("He had a stroke 10 minutes ago.")
        self.assertEqual(result["response_type"], "emergency_alert")
        self.assertIn("stroke_warning", result["warning_signs"])

    def test_negated_sign_does_not_suppress_another_emergency_sign(self):
        result, _ = respond("No chest pain, but severe bleeding.")
        self.assertEqual(result["response_type"], "emergency_alert")
        self.assertIn("severe_bleeding", result["warning_signs"])
        self.assertNotIn("chest_pain", result["warning_signs"])

    def test_still_present_symptom_survives_historical_wording(self):
        messages = (
            "I had chest pain yesterday and still have it.",
            "I had chest pain yesterday, but I still have the same pain.",
        )
        for message in messages:
            with self.subTest(message=message):
                result, _ = respond(message)
                self.assertEqual(result["response_type"], "emergency_alert")
                self.assertIn("chest_pain", result["warning_signs"])

    def test_unrelated_later_symptom_does_not_continue_historical_symptom(self):
        messages = (
            "I had chest pain yesterday. My cough is still here.",
            "I had chest pain yesterday: My cough is still here.",
            "I had chest pain yesterday while my cough is still here.",
        )
        for message in messages:
            with self.subTest(message=message):
                result = assess_emergency(message)
                self.assertNotIn("chest_pain", result["warning_signs"])

    def test_emergency_panel_does_not_duplicate_its_call_and_hospital_actions(self):
        script = (Path(__file__).resolve().parent.parent / "static/portal/chatbot.js").read_text()
        self.assertIn("new Set(['tel:112', '/hospitals/'])", script)
        self.assertIn(".filter((action) => !emergencyLinksAlreadyRendered.has(action.href))", script)

    def test_loss_of_consciousness_variants_are_screened(self):
        for message in ("I passed out.", "I fainted."):
            with self.subTest(message=message):
                self.assertIn("unconsciousness", assess_emergency(message)["warning_signs"])

    def test_page_confusion_and_definition_question_are_not_emergency_alerts(self):
        for message in (
            "I'm confused about how to use this page.",
            "What does suicidal mean?",
        ):
            with self.subTest(message=message):
                self.assertFalse(assess_emergency(message)["is_emergency"])

    def test_negation_constructions_and_positive_chest_pain(self):
        for message in ("I don't have chest pain.", "I can't have chest pain.", "I lack chest pain."):
            with self.subTest(message=message):
                self.assertNotIn("chest_pain", assess_emergency(message)["warning_signs"])
        self.assertIn("chest_pain", assess_emergency("I have severe chest pain.")["warning_signs"])

    def test_non_emergency_health_message_is_not_escalated(self):
        self.assertFalse(assess_emergency("I have had a mild cough for two days")["is_emergency"])

    def test_emergency_precedes_normal_intent_handling(self):
        result, state = respond("I cannot breathe, find hospitals in Pune")
        self.assertEqual(result["intent"], "medical_emergency")
        self.assertEqual(result["response_type"], "emergency_alert")
        self.assertIn("Do not wait", result["reply"])
        self.assertEqual(state["stage"], "emergency")
        self.assertEqual(state["pending_information"], [])

    def test_emergency_response_contract_and_call_action(self):
        result, _ = respond("I have severe chest pain")
        self.assertEqual(result["response_type"], "emergency_alert")
        self.assertEqual(result["warning_signs"], ["chest_pain"])
        self.assertIsNone(result["first_aid"])
        self.assertTrue(any(action["href"] == "tel:112" for action in result["actions"]))

    def test_normal_chat_response_contract_remains_compatible(self):
        result, _ = respond("I have a cough")
        self.assertIn("reply", result)
        self.assertEqual(result["intent"], "general_health")
        self.assertEqual(result["response_type"], "assistant_message")
        self.assertFalse(result["emergency"])


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class EmergencySummaryFlowTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user("emergency-patient", password="Strong-test-password-55")
        self.other = User.objects.create_user("other-emergency-patient", password="Strong-test-password-55")
        self.client = Client(enforce_csrf_checks=True)

    def get_csrf_token(self):
        response = self.client.get(reverse("emergency"))
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="csrfmiddlewaretoken" value="([^\"]+)"', response.content)
        self.assertIsNotNone(match, "Emergency form should render Django's CSRF input")
        return match.group(1).decode()

    def post_summary(self, data, token=None):
        headers = {"HTTP_X_CSRFTOKEN": token} if token else {}
        return self.client.post(
            reverse("api_emergency_summary"),
            data=json.dumps(data),
            content_type="application/json",
            **headers,
        )

    def test_summary_submission_is_csrf_protected(self):
        self.client.get(reverse("emergency"))
        rejected = self.post_summary({"reported_facts": {"symptoms": "Chest pain"}})
        self.assertEqual(rejected.status_code, 403)
        token = self.get_csrf_token()
        accepted = self.post_summary({"reported_facts": {"symptoms": "Chest pain"}}, token)
        self.assertEqual(accepted.status_code, 200)

    def test_authenticated_save_persists_to_current_patient(self):
        self.client.force_login(self.patient)
        token = self.get_csrf_token()
        response = self.post_summary({
            "reported_facts": {"symptoms": "Chest pain", "onset": "Just now"},
            "save": True,
        }, token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["saved"])
        case = EmergencyCase.objects.get()
        self.assertEqual(case.user, self.patient)
        self.assertIn("Symptoms reported", case.reported_facts)

    def test_optional_facts_may_be_missing(self):
        response = self.post_summary({"reported_facts": {}}, self.get_csrf_token())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reported_facts"], {})

    def test_invalid_field_types_and_oversized_values_are_rejected(self):
        token = self.get_csrf_token()
        for facts in ({"temperature": {"value": 37}}, {"symptoms": "x" * 1001}):
            with self.subTest(facts=tuple(facts)):
                response = self.post_summary({"reported_facts": facts}, token)
                self.assertEqual(response.status_code, 400)

    def test_save_request_requires_authentication(self):
        response = self.post_summary({"reported_facts": {}, "save": True}, self.get_csrf_token())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(EmergencyCase.objects.count(), 0)

    def test_public_handover_can_be_created_without_saving(self):
        response = self.post_summary({"reported_facts": {"symptoms": "Reported symptom"}}, self.get_csrf_token())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["saved"])
        self.assertEqual(EmergencyCase.objects.count(), 0)

    def test_invalid_consented_coordinates_are_rejected(self):
        self.client.force_login(self.patient)
        token = self.get_csrf_token()
        invalid_coordinates = (
            {},
            {"latitude": "north", "longitude": 10},
            {"latitude": True, "longitude": 10},
            {"latitude": 10, "longitude": False},
            {"latitude": 10**400, "longitude": 10},
            {"latitude": float("nan"), "longitude": 10},
            {"latitude": 10, "longitude": float("inf")},
            {"latitude": 100, "longitude": 10},
            {"latitude": 10, "longitude": -181},
        )
        for coordinates in invalid_coordinates:
            with self.subTest(coordinates=coordinates):
                response = self.post_summary({
                    "reported_facts": {}, "location_consent": True, "save": True, **coordinates,
                }, token)
                self.assertEqual(response.status_code, 400)
        self.assertFalse(EmergencyCase.objects.filter(user=self.patient).exists())

    def test_valid_coordinate_boundaries_are_accepted_and_saved(self):
        self.client.force_login(self.patient)
        token = self.get_csrf_token()
        for latitude, longitude, expected in ((-90, -180, "-90.00000, -180.00000"), (90, 180, "90.00000, 180.00000")):
            with self.subTest(latitude=latitude, longitude=longitude):
                response = self.post_summary({
                    "reported_facts": {}, "location_consent": True,
                    "latitude": latitude, "longitude": longitude, "save": True,
                }, token)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["location_shared"])
                self.assertEqual(response.json()["reported_facts"]["Location shared by user"], expected)
                saved = EmergencyCase.objects.order_by("-pk").first()
                self.assertEqual(saved.user, self.patient)
                self.assertEqual(float(saved.latitude), float(latitude))
                self.assertEqual(float(saved.longitude), float(longitude))

    def test_saved_summary_list_and_detail_are_patient_scoped(self):
        own = EmergencyCase.objects.create(user=self.patient, reported_facts={"Symptoms reported": "Own"})
        other = EmergencyCase.objects.create(user=self.other, reported_facts={"Symptoms reported": "Private"})
        self.client.force_login(self.patient)
        listing = self.client.get(reverse("emergency_summaries"))
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, "Private")
        self.assertContains(listing, reverse("emergency_summary_detail", args=[own.pk]))
        self.assertNotContains(listing, reverse("emergency_summary_detail", args=[other.pk]))
        detail = self.client.get(reverse("emergency_summary_detail", args=[own.pk]))
        self.assertContains(detail, "Own")
        self.assertEqual(self.client.get(reverse("emergency_summary_detail", args=[other.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("emergency_summary_detail", args=[other.pk + 1000])).status_code, 404)

    def test_summary_history_requires_authentication_and_empty_history_is_friendly(self):
        self.assertEqual(self.client.get(reverse("emergency_summaries")).status_code, 302)
        self.assertEqual(self.client.get(reverse("emergency_summary_detail", args=[1])).status_code, 302)
        self.client.force_login(self.patient)
        self.assertContains(self.client.get(reverse("emergency_summaries")), "No saved summaries yet")

    def test_dashboard_includes_saved_summary_section(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emergency summaries")

    def test_handover_page_shows_errors_and_prevents_duplicate_clicks(self):
        response = self.client.get(reverse("emergency"))
        self.assertContains(response, "Network error")
        self.assertContains(response, "Your entries are still here")
        self.assertContains(response, "if (button.disabled) return")
        self.assertContains(response, "button.disabled = true")
        self.assertContains(response, "service returned an unreadable response")
