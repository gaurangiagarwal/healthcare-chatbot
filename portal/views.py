import json
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .services.chat import respond
from .services.resources import (
    generate_emergency_summary, get_emergency_contacts, get_hospital_details,
    retrieve_first_aid_guide, search_doctors, search_hospitals,
)
from .services.first_aid import list_first_aid_guides
from .services.safety import assess_emergency
from .forms import (
    RegisterForm, ProfileForm, MedicalNoteForm, EmergencyContactForm,
    HospitalEnquiryForm, ReferralForm, HospitalProfileForm, HospitalServiceForm,
)
from .models import (
    PatientProfile, Doctor, AppointmentSlot, Appointment, ChatConversation,
    ChatMessage, MedicalNote, Hospital, HospitalService, HospitalAdministrator,
    EmergencyContact, EmergencyCase, Referral, HospitalEnquiry, AuditLog,
)

def home(request): return render(request, "portal/home.html")

def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); PatientProfile.objects.create(user=user); login(request, user)
        messages.success(request, "Your patient account is ready."); return redirect("dashboard")
    return render(request, "portal/form_page.html", {"form": form, "title": "Create your account"})

@login_required
def dashboard(request):
    return render(request, "portal/dashboard.html", {
        "recent_conversations": request.user.chat_conversations.all()[:4],
        "recent_contacts": request.user.emergency_contacts.all()[:4],
        "recent_referrals": request.user.referrals.select_related("hospital")[:4],
        "chats_count": request.user.chat_messages.filter(role="user").count(),
    })

@login_required
def profile(request):
    instance, _ = PatientProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=instance, user=request.user)
    if request.method == "POST" and form.is_valid(): form.save(); messages.success(request, "Profile saved."); return redirect("profile")
    return render(request, "portal/form_page.html", {"form": form, "title": "My profile"})

@login_required
def chatbot(request):
    conversation_id = request.GET.get("conversation")
    conversation = ChatConversation.objects.filter(pk=conversation_id, patient=request.user).first() if conversation_id else None
    if conversation is None:
        conversation = _active_conversation(request)
    else:
        request.session["active_chat_conversation_id"] = conversation.pk
    history = list(conversation.messages.order_by("-created_at")[:40])
    history.reverse()
    return render(request, "portal/chatbot.html", {
        "history": history, "conversation": conversation,
        "conversations": request.user.chat_conversations.all()[:12],
    })


def _active_conversation(request):
    """Fetch this session's thread only when it belongs to the current user."""
    conversation_id = request.session.get("active_chat_conversation_id")
    conversation = ChatConversation.objects.filter(pk=conversation_id, patient=request.user).first() if conversation_id else None
    if conversation is None:
        conversation = ChatConversation.objects.create(patient=request.user)
        request.session["active_chat_conversation_id"] = conversation.pk
    return conversation


@login_required
def new_chat(request):
    if request.method != "POST":
        return redirect("chatbot")
    conversation = ChatConversation.objects.create(patient=request.user)
    request.session["active_chat_conversation_id"] = conversation.pk
    return redirect("chatbot")

@login_required
def chat_send(request):
    if request.method != "POST": return JsonResponse({"error": "POST required"}, status=405)
    try: payload = json.loads(request.body); message = str(payload.get("message", "")).strip()
    except (json.JSONDecodeError, AttributeError): return JsonResponse({"error": "Invalid request"}, status=400)
    if not message or len(message) > 2000: return JsonResponse({"error": "Enter a message up to 2,000 characters."}, status=400)
    conversation_id = payload.get("conversation_id")
    if conversation_id:
        conversation = get_object_or_404(ChatConversation, pk=conversation_id, patient=request.user)
        request.session["active_chat_conversation_id"] = conversation.pk
    else:
        conversation = _active_conversation(request)
    response, state = respond(
        message,
        conversation.state,
        user=request.user,
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
    )
    conversation.state = state
    conversation.save(update_fields=["state", "updated_at"])
    ChatMessage.objects.bulk_create([
        ChatMessage(patient=request.user, conversation=conversation, role="user", content=message),
        ChatMessage(patient=request.user, conversation=conversation, role="bot", content=response["reply"]),
    ])
    return JsonResponse(response)

def doctor_list(request):
    doctors = Doctor.objects.select_related("hospital").all()
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


def hospitals_page(request):
    filters = {
        "query": request.GET.get("q", "").strip(),
        "location": request.GET.get("location", "").strip(),
        "latitude": request.GET.get("lat"),
        "longitude": request.GET.get("lon"),
        "emergency": request.GET.get("emergency") == "1",
        "icu": request.GET.get("icu") == "1",
        "trauma": request.GET.get("trauma") == "1",
        "specialty": request.GET.get("specialty", "").strip(),
    }
    hospitals = search_hospitals(**filters)
    return render(request, "portal/hospitals.html", {"hospitals": hospitals, "map_hospitals": hospitals, "filters": filters})


def hospitals_api(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    results = search_hospitals(
        query=request.GET.get("q", ""),
        location=request.GET.get("location", ""),
        latitude=request.GET.get("lat"),
        longitude=request.GET.get("lon"),
        emergency=request.GET.get("emergency") == "1",
        icu=request.GET.get("icu") == "1",
        trauma=request.GET.get("trauma") == "1",
        specialty=request.GET.get("specialty", ""),
    )
    return JsonResponse({"results": results})


def hospital_details_api(request, hospital_id):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    hospital = get_hospital_details(hospital_id)
    if hospital is None:
        return JsonResponse({"error": "Hospital not found"}, status=404)
    return JsonResponse(hospital)


def doctors_api(request):
    return JsonResponse({"results": search_doctors(
        specialty=request.GET.get("specialty", ""),
        location=request.GET.get("location", ""),
        query=request.GET.get("q", ""),
    )})


def first_aid_page(request, category=None):
    if category:
        guide = retrieve_first_aid_guide(category)
        if guide is None:
            return render(request, "portal/not_found.html", status=404)
        return render(request, "portal/first_aid_detail.html", {"guide": guide})
    return render(request, "portal/first_aid.html", {"guides": list_first_aid_guides()})


def first_aid_api(request, category=None):
    if category:
        guide = retrieve_first_aid_guide(category)
        if guide is None:
            return JsonResponse({"error": "Guide not found"}, status=404)
        return JsonResponse(guide)
    return JsonResponse({"results": list_first_aid_guides()})


def emergency_assistance(request):
    return render(request, "portal/emergency.html", {"emergency_number": "112"})


def emergency_summary_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        payload = json.loads(request.body)
        facts = payload.get("reported_facts", {})
        if not isinstance(facts, dict):
            return JsonResponse({"error": "reported_facts must be an object"}, status=400)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    for key in ("symptoms", "onset", "temperature", "relevant_information", "actions_taken"):
        if len(str(facts.get(key, ""))) > 1000:
            return JsonResponse({"error": f"{key} is too long"}, status=400)
    consent = payload.get("location_consent") is True
    summary = generate_emergency_summary(
        facts,
        location_consent=consent,
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
    )
    if payload.get("save") is True and request.user.is_authenticated:
        EmergencyCase.objects.create(
            user=request.user,
            reported_facts=summary["reported_facts"],
            location_shared=summary["location_shared"],
            latitude=payload.get("latitude") if summary["location_shared"] else None,
            longitude=payload.get("longitude") if summary["location_shared"] else None,
        )
        summary["saved"] = True
    else:
        summary["saved"] = False
    return JsonResponse(summary)


def emergency_contacts_api(request):
    if request.method == "GET":
        return JsonResponse(get_emergency_contacts(request.user))
    if request.method != "POST":
        return JsonResponse({"error": "GET or POST required"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in to save personal emergency contacts"}, status=401)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    form = EmergencyContactForm(payload)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    contact = form.save(commit=False)
    contact.user = request.user
    contact.save()
    return JsonResponse({"id": contact.pk, "name": contact.name, "phone": contact.phone, "relationship": contact.relationship}, status=201)


@login_required
def emergency_profile(request):
    form = EmergencyContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        contact = form.save(commit=False)
        contact.user = request.user
        contact.save()
        messages.success(request, "Emergency contact saved to your account.")
        return redirect("emergency_profile")
    return render(request, "portal/emergency_profile.html", {"form": form, "contacts": request.user.emergency_contacts.all()})


@login_required
def delete_emergency_contact(request, contact_id):
    if request.method != "POST":
        return redirect("emergency_profile")
    contact = get_object_or_404(EmergencyContact, pk=contact_id, user=request.user)
    contact.delete()
    messages.success(request, "Emergency contact removed.")
    return redirect("emergency_profile")


@login_required
def referrals_page(request):
    form = ReferralForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        referral = form.save(commit=False)
        referral.patient = request.user
        referral.save()
        messages.success(request, "Demonstration referral enquiry submitted.")
        return redirect("my_referrals")
    return render(request, "portal/referral_form.html", {"form": form})


@login_required
def my_referrals(request):
    return render(request, "portal/referrals.html", {"referrals": request.user.referrals.select_related("hospital")})


@login_required
def referrals_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    form = ReferralForm(payload)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    referral = form.save(commit=False)
    referral.patient = request.user
    referral.save()
    return JsonResponse({"id": referral.pk, "status": referral.status, "hospital": referral.hospital.name}, status=201)


def hospital_enquiry(request):
    form = HospitalEnquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.patient = request.user if request.user.is_authenticated else None
        enquiry.save()
        messages.success(request, "Demonstration enquiry received. This is not an admission request.")
        return redirect("hospital_detail", hospital_id=enquiry.hospital_id)
    return render(request, "portal/enquiry_form.html", {"form": form})


def hospital_detail(request, hospital_id):
    hospital = get_object_or_404(Hospital.objects.prefetch_related("services", "doctors"), pk=hospital_id)
    return render(request, "portal/hospital_detail.html", {"hospital": hospital})


def _hospital_admin_profile(request):
    return HospitalAdministrator.objects.select_related("hospital").filter(user=request.user).first()


def hospital_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if _hospital_admin_profile(request) is None:
            raise PermissionDenied("Hospital administrator access is required.")
        return view(request, *args, **kwargs)
    return wrapped


@hospital_admin_required
def hospital_admin_dashboard(request):
    profile = _hospital_admin_profile(request)
    hospital = profile.hospital
    return render(request, "portal/hospital_admin/dashboard.html", {
        "hospital": hospital,
        "services": hospital.services.all(),
        "enquiries": hospital.enquiries.select_related("patient")[:20],
        "referrals": hospital.referrals.select_related("patient")[:20],
        "audit_logs": hospital.audit_events.select_related("administrator")[:20],
        "form": HospitalProfileForm(instance=hospital),
    })


@hospital_admin_required
def hospital_admin_profile_update(request):
    profile = _hospital_admin_profile(request)
    form = HospitalProfileForm(request.POST, instance=profile.hospital)
    if request.method != "POST" or not form.is_valid():
        return render(request, "portal/hospital_admin/dashboard.html", {"hospital": profile.hospital, "services": profile.hospital.services.all(), "enquiries": profile.hospital.enquiries.all()[:20], "referrals": profile.hospital.referrals.all()[:20], "form": form}, status=400)
    form.save()
    AuditLog.objects.create(administrator=request.user, hospital=profile.hospital, action="profile_updated", details={"fields": list(form.changed_data)})
    messages.success(request, "Hospital profile updated.")
    return redirect("hospital_admin")


@hospital_admin_required
def hospital_admin_service_update(request, service_id):
    profile = _hospital_admin_profile(request)
    service = get_object_or_404(HospitalService, pk=service_id, hospital=profile.hospital)
    form = HospitalServiceForm(request.POST, instance=service)
    if request.method != "POST" or not form.is_valid():
        messages.error(request, "Service update was not valid.")
        return redirect("hospital_admin")
    updated = form.save(commit=False)
    updated.updated_by = request.user
    updated.save()
    AuditLog.objects.create(administrator=request.user, hospital=profile.hospital, action="service_updated", details={"service_id": service.pk, "status": service.status, "source": service.source})
    messages.success(request, "Service information updated; it will display as unknown after expiry.")
    return redirect("hospital_admin")


@hospital_admin_required
def hospital_admin_services_api(request):
    profile = _hospital_admin_profile(request)
    if request.method == "GET":
        return JsonResponse({"results": [
            {"id": service.pk, "type": service.service_type, "specialty": service.specialty_name, "status": service.effective_status, "source": service.source, "updated_at": service.updated_at.isoformat(), "expires_at": service.expires_at.isoformat() if service.expires_at else None}
            for service in profile.hospital.services.all()
        ]})
    if request.method != "PUT":
        return JsonResponse({"error": "GET or PUT required"}, status=405)
    try:
        payload = json.loads(request.body)
        updates = payload.get("services")
        if not isinstance(updates, list):
            return JsonResponse({"error": "services must be an array"}, status=400)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    results = []
    for item in updates:
        service_id = item.get("id")
        service = get_object_or_404(HospitalService, pk=service_id, hospital=profile.hospital)
        form = HospitalServiceForm(item, instance=service)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        service = form.save(commit=False)
        service.updated_by = request.user
        service.save()
        AuditLog.objects.create(administrator=request.user, hospital=profile.hospital, action="service_updated", details={"service_id": service.pk, "status": service.status, "source": service.source})
        results.append({"id": service.pk, "status": service.effective_status})
    return JsonResponse({"updated": results})


@hospital_admin_required
def hospital_admin_enquiries_api(request):
    profile = _hospital_admin_profile(request)
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    return JsonResponse({"results": [
        {"id": item.pk, "hospital": item.hospital.name, "message": item.message, "status": item.status, "created_at": item.created_at.isoformat()}
        for item in profile.hospital.enquiries.all()
    ]})


@hospital_admin_required
def update_referral_status(request, referral_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "PATCH required"}, status=405)
    profile = _hospital_admin_profile(request)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    status = payload.get("status")
    allowed = {value for value, _ in Referral.STATUS_CHOICES}
    referral = get_object_or_404(Referral, pk=referral_id, hospital=profile.hospital)
    if status not in allowed:
        return JsonResponse({"error": "Invalid referral status"}, status=400)
    referral.status = status
    referral.save(update_fields=["status", "updated_at"])
    AuditLog.objects.create(administrator=request.user, hospital=profile.hospital, action="referral_status_updated", details={"referral_id": referral.pk, "status": status})
    return JsonResponse({"id": referral.pk, "status": referral.status})


@hospital_admin_required
def update_enquiry_status(request, enquiry_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "PATCH required"}, status=405)
    profile = _hospital_admin_profile(request)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    status = payload.get("status")
    allowed = {value for value, _ in HospitalEnquiry.STATUS_CHOICES}
    enquiry = get_object_or_404(HospitalEnquiry, pk=enquiry_id, hospital=profile.hospital)
    if status not in allowed:
        return JsonResponse({"error": "Invalid enquiry status"}, status=400)
    enquiry.status = status
    enquiry.save(update_fields=["status", "updated_at"])
    AuditLog.objects.create(administrator=request.user, hospital=profile.hospital, action="enquiry_status_updated", details={"enquiry_id": enquiry.pk, "status": status})
    return JsonResponse({"id": enquiry.pk, "status": enquiry.status})
