"""Intent routing and structured assistant responses backed by real app services."""
import re

from portal.chatbot import process_message
from portal.services.first_aid import get_first_aid_guide
from portal.services.resources import search_doctors, search_hospitals
from portal.services.safety import assess_emergency


def _first_aid_category(text):
    for words, slug in (
        (("burn", "scald"), "burns"),
        (("bleed", "bleeding"), "bleeding"),
        (("chok",), "choking"),
        (("fracture", "broken bone", "broke my"), "fractures"),
        (("seizure", "convulsion", "fitting"), "seizures"),
        (("stroke", "face droop", "slurred speech"), "stroke"),
        (("heart attack", "cardiac"), "cardiac"),
        (("allergic reaction", "anaphylaxis", "throat swelling"), "allergic-reaction"),
    ):
        if any(word in text for word in words):
            return slug
    return None


def _hospital_intent(text):
    return bool(re.search(r"\b(?:hospital|hospitals|emergency department|icu|trauma centre|trauma center)\b", text))


def _hospital_filters(text):
    cities = ("Pune", "Mumbai", "Delhi", "Bengaluru", "Bangalore")
    location = next((city for city in cities if city.lower() in text), "")
    specialty = next((item for item in ("Cardiology", "Dermatology", "Pediatrics", "Family Medicine") if item.lower() in text), "")
    return {
        "location": location,
        "emergency": bool(re.search(r"\b(?:emergency|emergency department)\b", text)),
        "icu": bool(re.search(r"\bicu\b", text)),
        "trauma": bool(re.search(r"\btrauma\b", text)),
        "specialty": specialty,
    }


def _doctor_intent(text):
    return bool(re.search(r"\b(?:doctor|doctors|cardiologist|dermatologist|pediatrician|specialist|physician)\b", text))


def _doctor_specialty(text, state):
    if re.search(r"\b(?:child|children|kid|son|daughter|baby|infant|pediatrician)\b", text):
        return "Pediatrics"
    if re.search(r"\b(?:rash|skin|mole|acne|dermatologist)\b", text):
        return "Dermatology"
    if re.search(r"\b(?:heart|cardiac|cardiologist)\b", text):
        return "Cardiology"
    if state.get("symptoms"):
        return "Family Medicine"
    return ""


def respond(message, state=None, user=None, latitude=None, longitude=None):
    """Return (structured response, next conversation state)."""
    state = state or {}
    text = message.lower()
    emergency = assess_emergency(message)
    if emergency["is_emergency"]:
        next_state = dict(state)
        next_state["emergency_warning_signs"] = list(dict.fromkeys(
            [*next_state.get("emergency_warning_signs", []), *emergency["matched_warning_signs"]]
        ))
        next_state["last_question"] = None
        next_state["pending_information"] = []
        next_state["stage"] = "emergency"
        return ({
            "reply": emergency["message"],
            "intent": "medical_emergency",
            "response_type": "emergency_alert",
            "emergency": True,
            "emergency_number": emergency["emergency_number"],
            "urgency_level": emergency["urgency_level"],
            "matched_warning_signs": emergency["matched_warning_signs"],
            "actions": [{"label": "Call 112", "href": "tel:112"}, {"label": "Find nearby hospitals", "href": "/hospitals/"}],
            "first_aid": None,
            "warning_signs": emergency["warning_signs"],
        }, next_state)

    guide_slug = _first_aid_category(text)
    if guide_slug and re.search(r"\b(?:first aid|what should i do|help with|how to help|guide)\b", text):
        guide = get_first_aid_guide(guide_slug)
        return ({
            "reply": f"Here is the reviewed public first-aid guide for {guide['title']}. Call 112 if the situation is urgent.",
            "intent": "first_aid",
            "response_type": "first_aid_guide",
            "emergency": False,
            "first_aid": guide,
            "actions": [{"label": "Call 112", "href": "tel:112"}, {"label": "Open first-aid centre", "href": f"/first-aid/{guide_slug}/"}],
        }, state)

    if _hospital_intent(text):
        filters = _hospital_filters(text)
        hospitals = search_hospitals(
            location=filters["location"],
            latitude=latitude,
            longitude=longitude,
            emergency=filters["emergency"],
            icu=filters["icu"],
            trauma=filters["trauma"],
            specialty=filters["specialty"],
        )
        return ({
            "reply": f"Found {len(hospitals)} matching directory record(s). Demo records are not verified; call a facility using only a verified number shown in its profile.",
            "intent": "hospital_discovery",
            "response_type": "hospital_results",
            "emergency": False,
            "hospitals": hospitals[:5],
            "actions": [{"label": "Open hospital finder", "href": "/hospitals/"}],
        }, state)

    if _doctor_intent(text):
        specialty = _doctor_specialty(text, state)
        doctors = search_doctors(specialty=specialty)
        if specialty:
            reply = f"{specialty} is a reasonable type of clinician to consult based on what you shared. I cannot diagnose or prescribe. Directory profiles are demo records unless marked otherwise."
        else:
            reply = "I can search the doctor directory. Tell me the specialty or open Find hospitals to browse demo affiliations. I cannot diagnose or prescribe."
        return ({
            "reply": reply,
            "intent": "doctor_discovery",
            "response_type": "doctor_results",
            "emergency": False,
            "doctors": doctors[:5],
            "actions": [{"label": "Open doctor directory", "href": "/doctors/"}],
        }, state)

    if re.search(r"\b(?:referral|refer me|send my details|enquiry|inquiry)\b", text):
        return ({
            "reply": "I can prepare a demonstration enquiry for a hospital. This does not submit a referral until you review and submit the form.",
            "intent": "referral_enquiry",
            "response_type": "referral_action",
            "emergency": False,
            "actions": [{"label": "Create an enquiry", "href": "/referrals/new/"}],
        }, state)

    reply, next_state = process_message(message, state)
    if re.search(r"\b(?:112|emergency number|emergency contact)\b", text):
        return ({
            "reply": "India's emergency response number is 112. Use the call action if this is an emergency.",
            "intent": "emergency_contact",
            "response_type": "emergency_contact",
            "emergency": False,
            "emergency_number": "112",
            "actions": [{"label": "Call 112", "href": "tel:112"}],
        }, next_state)
    return ({"reply": reply, "intent": "general_health", "response_type": "assistant_message", "emergency": False}, next_state)
