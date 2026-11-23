import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from portal.services.chat import respond
from portal.services.ollama import generate_general_reply


class StructuredChatFlowTests(SimpleTestCase):
    def test_emergency_screening_precedes_local_ai(self):
        with patch("portal.services.chat.generate_general_reply") as generate:
            result, state = respond("I have severe chest pain")
        self.assertEqual(result["response_type"], "emergency_alert")
        self.assertTrue(any(action["href"] == "tel:112" for action in result["actions"]))
        self.assertIn("Do not wait", result["reply"])
        generate.assert_not_called()

    def test_negated_symptom_does_not_start_guided_flow(self):
        result, state = respond("I don't have a cough")
        self.assertNotIn("health_flow", state)
        self.assertNotEqual(result["response_type"], "symptom_followup")

    def test_historical_symptom_is_not_treated_as_current(self):
        result, state = respond("I had a cough last week")
        self.assertEqual(result["intent"], "historical_symptom_context")
        self.assertNotIn("health_flow", state)
        self.assertIn("not treat it as current", result["reply"])

    def test_guided_flow_asks_one_question_at_a_time(self):
        first, state = respond("I have a cough")
        self.assertEqual(first["response_type"], "symptom_followup")
        self.assertEqual(first["question"], "When did it start?")
        self.assertEqual(first["flow_stage"], "awaiting_onset")
        second, state = respond("since yesterday", state)
        self.assertEqual(second["question"], "How severe is it right now: mild, moderate, or severe?")
        self.assertEqual(second["flow_stage"], "awaiting_severity")
        third, state = respond("moderate", state)
        self.assertEqual(third["question"], "Are you noticing any other symptoms?")
        self.assertEqual(third["flow_stage"], "awaiting_associated_symptoms")
        summary, state = respond("no other symptoms", state)
        self.assertEqual(summary["response_type"], "symptom_summary")
        self.assertIn("not a substitute for a clinician", summary["reply"])
        self.assertFalse(state["health_flow"]["active"])

    def test_existing_answers_are_not_requested_again(self):
        result, state = respond("I have a cough since yesterday and it is moderate")
        self.assertEqual(result["question"], "Are you noticing any other symptoms?")
        self.assertEqual(state["health_flow"]["onset"], "since yesterday")
        self.assertEqual(state["health_flow"]["severity"]["category"], "moderate")

    def test_stop_request_returns_to_normal_assistant(self):
        _, state = respond("I have a cough")
        result, state = respond("Stop symptom questions", state)
        self.assertEqual(result["intent"], "symptom_flow_stopped")
        self.assertFalse(state["health_flow"]["active"])

    def test_local_ai_is_only_used_for_general_fallback(self):
        with patch("portal.services.chat.generate_general_reply", return_value=("Cautious general information.\n\nGeneral information only; this is not a substitute for a clinician.", "ok")) as generate:
            result, _ = respond("What is dehydration?")
        self.assertEqual(result["response_mode"], "local_ai")
        self.assertFalse(result["emergency"])
        generate.assert_called_once_with("What is dehydration?")

    def test_unavailable_ai_uses_existing_deterministic_fallback(self):
        with patch("portal.services.chat.generate_general_reply", return_value=(None, "unavailable")):
            result, _ = respond("What is dehydration?")
        self.assertEqual(result["response_mode"], "deterministic_fallback")
        self.assertIn("I don't have reliable guidance", result["reply"])

    def test_provider_source_and_trust_labels_are_preserved_without_ai(self):
        provider = {
            "result_id": "managed:hospital:7", "result_type": "hospital",
            "name": "Example facility", "source": "MediReach", "trust_label": "DEMO — fictional facility",
            "provider_status": "demo", "specialties": [], "services": [], "contacts": [], "sources": [],
        }
        with patch("portal.services.chat.discover_providers", return_value=[provider]), \
             patch("portal.services.chat.generate_general_reply") as generate:
            result, _ = respond("Find hospitals")
        self.assertEqual(result["providers"][0]["source"], "MediReach")
        self.assertIn("DEMO", result["providers"][0]["trust_label"])
        generate.assert_not_called()

    def test_chat_files_include_emergency_and_symptom_controls_safely(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        script = (root / "static/portal/chatbot.js").read_text(encoding="utf-8")
        template = (root / "templates/portal/chatbot.html").read_text(encoding="utf-8")
        self.assertIn("link('Call 112 now', 'tel:112'", script)
        self.assertIn("case 'symptom_followup'", script)
        self.assertIn("case 'symptom_summary'", script)
        self.assertIn("stop-symptom-flow", script)
        self.assertIn('id="stop-symptom-flow"', template)
        self.assertIn("bubble.textContent = text", script)


class OllamaFallbackTests(SimpleTestCase):
    def test_unconfigured_local_ai_returns_deterministic_fallback_status(self):
        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "", "OLLAMA_MODEL": ""}, clear=False):
            reply, status = generate_general_reply("What is hydration?")
        self.assertIsNone(reply)
        self.assertEqual(status, "not_configured")

    def test_malformed_local_ai_response_is_rejected(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return b'{"unexpected": true}'

        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://127.0.0.1:11434", "OLLAMA_MODEL": "local-model"}), \
             patch("portal.services.ollama.urlopen", return_value=FakeResponse()):
            reply, status = generate_general_reply("What is hydration?")
        self.assertIsNone(reply)
        self.assertEqual(status, "malformed_or_unsafe")

    def test_unsafe_model_output_is_rejected(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return json.dumps({"message": {"content": "You have pneumonia. Take 2 tablets daily."}}).encode()

        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://127.0.0.1:11434", "OLLAMA_MODEL": "local-model"}), \
             patch("portal.services.ollama.urlopen", return_value=FakeResponse()):
            reply, status = generate_general_reply("What is this cough?")
        self.assertIsNone(reply)
        self.assertEqual(status, "malformed_or_unsafe")

    def test_unavailable_local_ai_returns_none(self):
        from urllib.error import URLError
        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://127.0.0.1:11434", "OLLAMA_MODEL": "local-model"}), \
             patch("portal.services.ollama.urlopen", side_effect=URLError("offline")):
            reply, status = generate_general_reply("What is hydration?")
        self.assertIsNone(reply)
        self.assertEqual(status, "unavailable")

    def test_local_ai_timeout_returns_none(self):
        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://127.0.0.1:11434", "OLLAMA_MODEL": "local-model"}), \
             patch("portal.services.ollama.urlopen", side_effect=TimeoutError("slow")):
            reply, status = generate_general_reply("What is hydration?")
        self.assertIsNone(reply)
        self.assertEqual(status, "unavailable")


@override_settings(SECURE_SSL_REDIRECT=False)
class ConversationHistoryCompatibilityTests(TestCase):
    def test_guided_conversation_keeps_existing_message_and_state_storage(self):
        user = User.objects.create_user("p3-history-patient", password="Safe-test-password-77")
        self.client.force_login(user)
        page = self.client.get(reverse("chatbot"))
        self.assertEqual(page.status_code, 200)
        conversation_id = page.context["conversation"].pk
        response = self.client.post(
            reverse("chat_send"),
            data=json.dumps({"conversation_id": conversation_id, "message": "I have a cough", "latitude": 19.0, "longitude": 72.0}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["response_type"], "symptom_followup")
        from portal.models import ChatConversation, ChatMessage
        saved = ChatConversation.objects.get(pk=conversation_id, patient=user)
        self.assertTrue(saved.state["health_flow"]["active"])
        self.assertNotIn("latitude", saved.state)
        self.assertNotIn("longitude", saved.state)
        self.assertEqual(ChatMessage.objects.filter(conversation=saved).count(), 2)
