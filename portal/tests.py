import json
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .chatbot import reply
from .models import PatientProfile, Doctor, AppointmentSlot, Appointment, ChatMessage, MedicalNote

@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ChatbotRuleTests(TestCase):
    def test_supported_symptom(self): self.assertIn("How long", reply("I have a fever"))
    def test_unknown_fallback(self): self.assertIn("qualified healthcare professional", reply("What is the meaning of xyzzy?"))
    def test_emergency_escalation(self): self.assertIn("emergency", reply("I have chest pain"))
    def test_no_diagnosis_or_prescription(self):
        answer = reply("I have a cough")
        self.assertNotIn("diagnosed with", answer.lower()); self.assertNotIn("take 500mg", answer.lower())

@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class PatientFlowsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("patient1", "patient@example.test", "A-strong-pass-42", first_name="Asha")
        PatientProfile.objects.create(user=self.user)
        self.other = User.objects.create_user("patient2", "other@example.test", "A-strong-pass-42")
        PatientProfile.objects.create(user=self.other)
    def test_register_and_hash_password(self):
        response = self.client.post(reverse("register"), {"username":"newuser", "first_name":"New Patient", "email":"new@example.test", "password1":"G00dStrongPassword!", "password2":"G00dStrongPassword!"})
        self.assertRedirects(response, reverse("dashboard")); user=User.objects.get(username="newuser"); self.assertNotEqual(user.password, "G00dStrongPassword!")
    def test_duplicate_email_rejected(self):
        response=self.client.post(reverse("register"), {"username":"othername", "first_name":"Other", "email":"PATIENT@example.test", "password1":"G00dStrongPassword!", "password2":"G00dStrongPassword!"})
        self.assertEqual(response.status_code, 200); self.assertFalse(User.objects.filter(username="othername").exists())
    def test_dashboard_requires_login(self): self.assertRedirects(self.client.get(reverse("dashboard")), f"{reverse('login')}?next={reverse('dashboard')}")
    def test_login_invalid_credentials(self): self.assertEqual(self.client.post(reverse("login"), {"username":"patient1", "password":"wrong"}).status_code, 200)
    def test_profile_saved_to_own_user(self):
        self.client.force_login(self.user); response=self.client.post(reverse("profile"), {"first_name":"Asha Rao", "email":"patient@example.test", "age":31, "gender":"Prefer not to say", "phone":"1234567890", "health_information":"Allergy note"})
        self.assertRedirects(response, reverse("profile")); self.user.refresh_from_db(); self.assertEqual(self.user.first_name,"Asha Rao"); self.assertEqual(self.user.profile.health_information,"Allergy note")
    def test_chat_ajax_saves_both_messages_only_for_current_user(self):
        self.client.force_login(self.user); response=self.client.post(reverse("chat_send"), data=json.dumps({"message":"I have a cough"}), content_type="application/json")
        self.assertEqual(response.status_code,200); self.assertEqual(ChatMessage.objects.filter(patient=self.user).count(),2); self.assertEqual(ChatMessage.objects.filter(patient=self.other).count(),0)
    def test_chat_rejects_empty_message(self):
        self.client.force_login(self.user); response=self.client.post(reverse("chat_send"), data=json.dumps({"message":" "}), content_type="application/json"); self.assertEqual(response.status_code,400)
    def test_history_scoped_to_patient(self):
        ChatMessage.objects.create(patient=self.other, role="user", content="private other message"); self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("chat_history")), "private other message")
    def test_notes_are_patient_scoped(self):
        MedicalNote.objects.create(patient=self.other,title="private",body="not yours"); self.client.force_login(self.user); self.assertNotContains(self.client.get(reverse("notes")),"not yours")

@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class BookingFlowTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("patient",password="A-strong-pass-42"); PatientProfile.objects.create(user=self.user)
        self.other=User.objects.create_user("other",password="A-strong-pass-42"); PatientProfile.objects.create(user=self.other)
        self.doctor=Doctor.objects.create(name="Dr. Test",specialization="Family Medicine",experience=4,qualification="MBBS")
        self.slot=AppointmentSlot.objects.create(doctor=self.doctor,starts_at=timezone.now()+timedelta(days=2))
    def test_successful_booking(self):
        self.client.force_login(self.user); response=self.client.post(reverse("book_appointment",args=[self.slot.pk])); self.assertRedirects(response,reverse("appointments")); self.assertTrue(Appointment.objects.filter(patient=self.user,slot=self.slot,status="booked").exists())
    def test_taken_slot_rejected(self):
        Appointment.objects.create(patient=self.other,slot=self.slot); self.client.force_login(self.user); self.client.post(reverse("book_appointment",args=[self.slot.pk])); self.assertFalse(Appointment.objects.filter(patient=self.user,slot=self.slot).exists())
    def test_cancel_releases_slot(self):
        appt=Appointment.objects.create(patient=self.user,slot=self.slot); self.client.force_login(self.user); self.client.post(reverse("cancel_appointment",args=[appt.pk])); appt.refresh_from_db(); self.assertEqual(appt.status,"cancelled"); self.client.post(reverse("book_appointment",args=[self.slot.pk])); self.assertTrue(Appointment.objects.filter(patient=self.user,slot=self.slot,status="booked").exists())
    def test_cannot_cancel_another_patients_appointment(self):
        appt=Appointment.objects.create(patient=self.other,slot=self.slot); self.client.force_login(self.user); self.assertEqual(self.client.post(reverse("cancel_appointment",args=[appt.pk])).status_code,404)
    def test_past_slot_cannot_be_booked(self):
        past=AppointmentSlot.objects.create(doctor=self.doctor,starts_at=timezone.now()-timedelta(days=1)); self.client.force_login(self.user); self.client.post(reverse("book_appointment",args=[past.pk])); self.assertFalse(Appointment.objects.filter(slot=past).exists())
    def test_doctor_search(self):
        self.client.force_login(self.user); self.assertContains(self.client.get(reverse("doctors"),{"q":"Family"}),"Dr. Test"); self.assertNotContains(self.client.get(reverse("doctors"),{"q":"Neurology"}),"Dr. Test")
