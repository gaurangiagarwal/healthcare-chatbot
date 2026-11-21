import json
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .chatbot import reply
from .forms import RegisterForm, ProfileForm, MedicalNoteForm
from .models import PatientProfile, Doctor, AppointmentSlot, Appointment, ChatMessage, MedicalNote

def home(request): return render(request, "portal/home.html")

def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); PatientProfile.objects.create(user=user); login(request, user)
        messages.success(request, "Your patient account is ready."); return redirect("dashboard")
    return render(request, "portal/form_page.html", {"form": form, "title": "Create your account"})

@login_required
def dashboard(request):
    return render(request, "portal/dashboard.html", {"appointments": request.user.appointments.filter(status="booked", slot__starts_at__gte=timezone.now())[:3], "notes_count": request.user.medical_notes.count(), "chats_count": request.user.chat_messages.filter(role="user").count()})

@login_required
def profile(request):
    instance, _ = PatientProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=instance, user=request.user)
    if request.method == "POST" and form.is_valid(): form.save(); messages.success(request, "Profile saved."); return redirect("profile")
    return render(request, "portal/form_page.html", {"form": form, "title": "My profile"})

@login_required
def chatbot(request):
    history = request.user.chat_messages.all()[-40:]
    return render(request, "portal/chatbot.html", {"history": history})

@login_required
def chat_send(request):
    if request.method != "POST": return JsonResponse({"error": "POST required"}, status=405)
    try: payload = json.loads(request.body); message = str(payload.get("message", "")).strip()
    except (json.JSONDecodeError, AttributeError): return JsonResponse({"error": "Invalid request"}, status=400)
    if not message or len(message) > 2000: return JsonResponse({"error": "Enter a message up to 2,000 characters."}, status=400)
    response = reply(message)
    ChatMessage.objects.bulk_create([ChatMessage(patient=request.user, role="user", content=message), ChatMessage(patient=request.user, role="bot", content=response)])
    return JsonResponse({"reply": response})

@login_required
def doctor_list(request):
    doctors = Doctor.objects.all()
    query = request.GET.get("q", "").strip()
    if query: doctors = doctors.filter(specialization__icontains=query) | doctors.filter(name__icontains=query)
    return render(request, "portal/doctors.html", {"doctors": doctors.distinct(), "query": query})

@login_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    slots = doctor.slots.filter(starts_at__gt=timezone.now()).exclude(appointments__status="booked")
    return render(request, "portal/doctor_detail.html", {"doctor": doctor, "slots": slots})

@login_required
def book_appointment(request, slot_id):
    if request.method != "POST": return redirect("doctors")
    try:
        with transaction.atomic():
            slot = AppointmentSlot.objects.select_for_update().get(pk=slot_id, starts_at__gt=timezone.now())
            Appointment.objects.create(patient=request.user, slot=slot)
        messages.success(request, "Appointment booked.")
    except (AppointmentSlot.DoesNotExist, IntegrityError): messages.error(request, "That slot is no longer available. Please choose another.")
    return redirect("appointments")

@login_required
def appointments(request): return render(request, "portal/appointments.html", {"appointments": request.user.appointments.select_related("slot__doctor"), "now": timezone.now()})

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, patient=request.user)
    if request.method == "POST" and appointment.status == "booked": appointment.status = "cancelled"; appointment.save(update_fields=["status"]); messages.success(request, "Appointment cancelled; the slot is available again.")
    return redirect("appointments")

@login_required
def chat_history(request):
    query = request.GET.get("q", "").strip()
    items = request.user.chat_messages.all()
    if query: items = items.filter(content__icontains=query)
    return render(request, "portal/history.html", {"items": items, "query": query})

@login_required
def notes(request):
    form = MedicalNoteForm(request.POST or None)
    if request.method == "POST" and form.is_valid(): note = form.save(commit=False); note.patient = request.user; note.save(); messages.success(request, "Note saved privately."); return redirect("notes")
    return render(request, "portal/notes.html", {"form": form, "notes": request.user.medical_notes.all()})
