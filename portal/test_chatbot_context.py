import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .chatbot import detect_symptoms, parse_duration, parse_temperature, process_message
from .models import ChatConversation, PatientProfile


@override_settings(SECURE_SSL_REDIRECT=False)
class ChatbotParsingTests(TestCase):
    def test_detects_multiple_symptoms(self):
        self.assertEqual(detect_symptoms("I have fever and headache"), ["fever", "headache"])

    def test_negated_symptom_is_not_detected(self):
        self.assertEqual(detect_symptoms("I don't have a cough"), [])

    def test_negation_does_not_hide_a_symptom_after_but(self):
        self.assertEqual(detect_symptoms("I don't have a cough, but I have fever"), ["fever"])

    def test_recognizes_duration_phrases(self):
        examples = {
            "Since yesterday": "since yesterday",
            "for two days": "for 2 days",
            "since morning": "since this morning",
            "for three hours": "for 3 hours",
            "for one week": "for 1 week",
        }
        for phrase, expected in examples.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_duration(phrase), expected)

    def test_converts_fahrenheit_and_celsius(self):
        self.assertEqual(parse_temperature("101°F"), {"value": 101.0, "unit": "F", "celsius": 38.3})
        self.assertEqual(parse_temperature("100.5 F"), {"value": 100.5, "unit": "F", "celsius": 38.1})
        self.assertEqual(parse_temperature("38°C"), {"value": 38.0, "unit": "C", "fahrenheit": 100.4})
        self.assertEqual(parse_temperature("39 degrees Celsius"), {"value": 39.0, "unit": "C", "fahrenheit": 102.2})

    def test_first_turn_asks_about_duration_and_temperature(self):
        response, state = process_message("I have fever and headache", {})
        self.assertIn("How long", response)
        self.assertIn("measured your temperature", response)
        self.assertEqual(state["symptoms"], ["fever", "headache"])

    def test_follow_up_uses_symptom_context_duration_and_temperature(self):
        _, state = process_message("I have fever and headache", {})
        response, state = process_message("Since yesterday. My temperature is 101°F", state)
        self.assertIn("fever and headache since yesterday", response)
        self.assertIn("38.3°C", response)
        self.assertIn("other symptoms", response)
        self.assertEqual(state["duration"], "since yesterday")
        self.assertEqual(state["temperature"]["celsius"], 38.3)

    def test_no_other_symptoms_does_not_repeat_questions(self):
        _, state = process_message("I have fever and headache", {})
        _, state = process_message("Since yesterday and 101°F", state)
        response, state = process_message("No, just fever and headache", state)
        self.assertNotIn("How long", response)
        self.assertNotIn("Have you measured", response)
        self.assertEqual(state["stage"], "complete")

    def test_unrelated_message_does_not_inherit_old_symptoms(self):
        _, state = process_message("I have fever", {})
        response, state = process_message("How do I fix a bicycle tire?", state)
        self.assertIn("don't have reliable guidance", response)
        self.assertEqual(state["symptoms"], [])

    def test_emergency_warning_signs_escalate(self):
        examples = [
            "severe chest pain",
            "difficulty breathing",
            "I feel confused",
            "severe headache with neck stiffness",
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertIn("emergency", process_message(text, {})[0].lower())

    def test_unknown_message_gets_safe_fallback(self):
        self.assertIn("qualified healthcare professional", process_message("What is a quibbleflap?", {})[0])


@override_settings(SECURE_SSL_REDIRECT=False)
class ChatConversationIsolationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("context-one", password="Pass12345!", first_name="Asha")
        self.other = User.objects.create_user("context-two", password="Pass12345!")
        PatientProfile.objects.create(user=self.user)
        PatientProfile.objects.create(user=self.other)

    def post_message(self, client, message, conversation_id=None):
        data = {"message": message}
        if conversation_id is not None:
            data["conversation_id"] = conversation_id
        return client.post(reverse("chat_send"), data=json.dumps(data), content_type="application/json")

    def test_context_is_saved_per_authenticated_user_and_conversation(self):
        self.client.force_login(self.user)
        self.client.get(reverse("chatbot"))
        conversation = ChatConversation.objects.get(patient=self.user)
        self.post_message(self.client, "I have fever and headache", conversation.pk)
        conversation.refresh_from_db()
        self.assertEqual(conversation.state["symptoms"], ["fever", "headache"])

        other_client = self.client_class()
        other_client.force_login(self.other)
        other_client.get(reverse("chatbot"))
        other_conversation = ChatConversation.objects.get(patient=self.other)
        response = self.post_message(other_client, "Since yesterday and 101°F", other_conversation.pk)
        self.assertIn("don't have reliable guidance", response.json()["reply"])
        self.assertEqual(other_conversation.patient, self.other)

    def test_starting_new_conversation_resets_context(self):
        self.client.force_login(self.user)
        self.client.get(reverse("chatbot"))
        old_conversation = ChatConversation.objects.get(patient=self.user)
        self.post_message(self.client, "I have fever", old_conversation.pk)

        response = self.client.post(reverse("new_chat"))
        self.assertRedirects(response, reverse("chatbot"))
        new_conversation = ChatConversation.objects.filter(patient=self.user).exclude(pk=old_conversation.pk).get()
        self.assertEqual(new_conversation.state, {})
        self.assertNotEqual(new_conversation.pk, old_conversation.pk)

        reply = self.post_message(self.client, "Since yesterday", new_conversation.pk).json()["reply"]
        self.assertIn("don't have reliable guidance", reply)

    def test_conversation_id_cannot_be_used_by_another_patient(self):
        conversation = ChatConversation.objects.create(patient=self.user)
        self.client.force_login(self.other)
        response = self.post_message(self.client, "Since yesterday", conversation.pk)
        self.assertEqual(response.status_code, 404)
