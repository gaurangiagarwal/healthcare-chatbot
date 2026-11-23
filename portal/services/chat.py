"""Intent routing and structured assistant responses backed by real app services."""
import re

from portal.chatbot import FALLBACK, process_message
from portal.services.first_aid import get_first_aid_guide
from portal.services.ollama import generate_general_reply
from portal.services.knowledge import answer_known_question
from portal.services.resources import discover_providers
from portal.services.safety import assess_emergency
from portal.services.symptom_flow import handle_symptom_flow, is_historical_only, is_stop_request


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
    facility_search = bool(re.search(r"\b(?:find|search|show|locate)\b.+\b(?:near|in|around)\b", text))
    if facility_search and re.search(r"\b(?:dentist|dentistry|dental|doctor|doctors|cardiologist|dermatologist|pediatrician|neurologist|specialist|physician)\b", text):
        facility_search = False
    return bool(
        re.search(r"\b(?:hospital|hospitals|clinic|clinics|pharmacy|pharmacies|laboratory|laboratories|diagnostic cent(?:re|er)|imaging cent(?:re|er)|emergency department|icu|trauma cent(?:re|er))\b", text)
        or facility_search
    )


def _location_phrase(text):
    match = re.search(r"\b(?:near|in|around|at)\s+(.+?)\s*$", text, re.I)
    if not match:
        return ""
    value = re.sub(r"[?.!,;]+$", "", match.group(1)).strip()
    if value.casefold() in {"me", "my location", "here"}:
        return ""
    return value[:120]


def _facility_keyword(text, location):
    value = text
    if location:
        value = re.sub(r"\b(?:near|in|around|at)\s+" + re.escape(location) + r"\s*[?.!,;]*$", "", value, flags=re.I)
    value = re.sub(r"^\s*(?:please\s+)?(?:find|search(?:\s+for)?|show(?:\s+me)?|locate)\s+", "", value, flags=re.I)
    value = re.sub(r"\bwith\s+(?:(?:emergency|icu|trauma)\s+)?services\b", " ", value, flags=re.I)
    value = re.sub(r"\b(?:called|named|name|a|an|the|nearby|near|hospital|hospitals|clinic|clinics|facility|facilities|emergency|icu|trauma|services)\b", " ", value, flags=re.I)
    return " ".join(value.split()).strip(" .,?!")


def _hospital_filters(text):
    text = str(text or "")
    normalized = text.casefold()
    location = _location_phrase(text)
    specialty = next((item for item in ("Cardiology", "Dermatology", "Pediatrics", "Family Medicine", "Dentistry", "Neurology") if item.casefold() in normalized), "")
    query = _facility_keyword(text, location)
    facility_type = next((
        value for pattern, value in (
            (r"\bclinics?\b", "clinic"), (r"\bpharmacies?\b", "pharmacy"),
            (r"\blaborator(?:y|ies)|diagnostic cent(?:re|er)\b", "diagnostic_centre"),
            (r"\bimaging cent(?:re|er)\b", "imaging_centre"),
        ) if re.search(pattern, normalized)
    ), "")
    return {
        "location": location,
        "query": query,
        "emergency": bool(re.search(r"\b(?:emergency|emergency department)\b", normalized)),
        "icu": bool(re.search(r"\bicu\b", normalized)),
        "trauma": bool(re.search(r"\btrauma\b", normalized)),
        "specialty": specialty,
        "facility_type": facility_type,
    }


def _doctor_intent(text):
    return bool(re.search(r"\b(?:doctor|doctors|dentist|dentistry|cardiologist|cardiology|dermatologist|dermatology|pediatrician|paediatrician|neurologist|neurology|specialist|physician)\b", text))


def _doctor_specialty(text, state):
    if re.search(r"\b(?:child|children|kid|son|daughter|baby|infant|pediatrician)\b", text):
        return "Pediatrics"
    if re.search(r"\b(?:rash|skin|mole|acne|dermatologist)\b", text):
        return "Dermatology"
    if re.search(r"\b(?:heart|cardiac|cardiologist)\b", text):
        return "Cardiology"
    if re.search(r"\b(?:dentist|dentistry|dental)\b", text):
        return "Dentist"
    if re.search(r"\b(?:neurologist|neurology|brain specialist)\b", text):
        return "Neurology"
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
        if isinstance(next_state.get("health_flow"), dict):
            next_state["health_flow"] = {**next_state["health_flow"], "active": False, "stage": "interrupted_by_safety_screen"}
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

    known_answer = answer_known_question(message)
    if known_answer:
        return ({"reply": known_answer, "intent": "general_health", "response_type": "assistant_message",
                 "emergency": False, "response_mode": "curated"}, state)

    active_flow = state.get("health_flow")
    if is_stop_request(message) and isinstance(active_flow, dict) and active_flow.get("active"):
        next_state = dict(state)
        next_state["health_flow"] = {**active_flow, "active": False, "stage": "stopped"}
        next_state.update({
            "symptoms": [], "duration": None, "temperature": None,
            "reported_temperature": None, "temperature_unit": None,
            "last_question": None, "pending_information": [], "stage": "idle",
        })
        return ({
            "reply": "Symptom questions stopped. You can ask a general question or request help finding care.",
            "intent": "symptom_flow_stopped", "response_type": "assistant_message",
            "emergency": False, "flow_active": False, "actions": [],
        }, next_state)

    # A clear navigation/action request leaves an in-progress symptom flow intact
    # in history but stops collecting details so the request is handled normally.
    if isinstance(active_flow, dict) and active_flow.get("active") and (
        _hospital_intent(text) or _doctor_intent(text)
        or re.search(r"\b(?:first aid|referral|refer me|enquiry|inquiry)\b", text)
    ):
        state = dict(state)
        state["health_flow"] = {**active_flow, "active": False, "stage": "interrupted_for_navigation"}
    elif isinstance(active_flow, dict) and active_flow.get("active"):
        flow_result = handle_symptom_flow(message, state)
        if flow_result:
            return flow_result

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

    if re.search(r"\b(?:enquiry|inquiry|ask a hospital|contact a hospital)\b", text):
        return ({
            "reply": "I can prepare a local general enquiry for a facility. It is saved in MediReach and is not delivered to the hospital.",
            "intent": "hospital_enquiry",
            "response_type": "enquiry_action",
            "emergency": False,
            "actions": [{"label": "Prepare a general enquiry", "href": "/enquiries/new/"}],
        }, state)

    if _hospital_intent(text):
        filters = _hospital_filters(message)
        source_errors = []
        providers = discover_providers(
            result_types="hospital",
            query=filters["query"],
            location=filters["location"],
            facility_type=filters["facility_type"],
            latitude=latitude,
            longitude=longitude,
            include_osm=latitude is not None and longitude is not None or bool(filters["location"]),
            emergency=filters["emergency"],
            icu=filters["icu"],
            trauma=filters["trauma"],
            specialty=filters["specialty"],
            source_errors=source_errors,
        )
        hospitals = [item for item in providers if item["result_type"] == "hospital"]
        mapped_facilities = [item for item in providers if item["result_type"] == "osm_facility"]
        if filters["location"] and not latitude and not longitude and any(item.get("source") == "Location" for item in source_errors):
            reply = f"I could not resolve {filters['location']} to a search area, so I did not search mapped listings. Check the place name or try a nearby city."
            hospitals = []
            mapped_facilities = []
            providers = []
        elif not hospitals and not mapped_facilities:
            query_context = f" for {filters['query']}" if filters["query"] else ""
            reply = f"No matching facility record was found{query_context}. Try a nearby area or open the hospital finder. I did not substitute unrelated facilities."
        else:
            reply = f"Found {len(hospitals)} MediReach-managed record(s) and {len(mapped_facilities)} OpenStreetMap mapped listing(s). Mapped listings are not independently verified and do not confirm that a facility is open or available."
        if hospitals:
            reply += " Demo provider records are fictional; each result shows its own trust label."
        osm_error = next((item for item in source_errors if item.get("source") == "OpenStreetMap"), None)
        location_error = next((item for item in source_errors if item.get("source") == "Location"), None)
        if osm_error:
            reply += f" MediReach-managed results are shown if present. {osm_error['message']}"
        elif location_error:
            reply += f" The area could not be resolved for mapped nearby search; any managed results were matched against their stored text fields. {location_error['message']}"
        elif latitude is None or longitude is None:
            reply += " Share your location with the optional chat control to include nearby mapped listings."
        return ({
            "reply": reply,
            "intent": "hospital_discovery",
            "response_type": "hospital_results",
            "emergency": False,
            "hospitals": hospitals[:5],
            "mapped_facilities": mapped_facilities[:5],
            "providers": providers[:10],
            "source_errors": source_errors,
            "actions": [{"label": "Open hospital finder", "href": "/hospitals/"}],
        }, state)

    if _doctor_intent(text):
        specialty = _doctor_specialty(text, state)
        source_errors = []
        providers = discover_providers(
            result_types="doctor", specialty=specialty, location=_location_phrase(message),
            query="",
            facility_type="doctor",
            latitude=latitude, longitude=longitude,
            include_osm=latitude is not None and longitude is not None or bool(_location_phrase(message)),
            source_errors=source_errors,
        )
        doctors = [item for item in providers if item["result_type"] == "doctor"]
        mapped_facilities = [item for item in providers if item["result_type"] == "osm_facility"]
        if doctors:
            reply = f"Found {len(doctors)} MediReach doctor profile(s)."
            if mapped_facilities:
                reply += f" Also found {len(mapped_facilities)} OpenStreetMap-mapped doctor or dentist facility location(s); these are not individual doctor profiles or verified."
        elif mapped_facilities:
            reply = f"No individual doctor profile matched. Found {len(mapped_facilities)} OpenStreetMap-mapped doctor or dentist facility location(s); they are not verified doctor profiles."
        elif specialty:
            reply = f"No matching {specialty} doctor profile or mapped facility was found. Try a nearby area or open the doctor directory. I did not invent a provider."
        else:
            reply = "I can search the doctor directory. Tell me the specialty or open the doctor directory. I cannot diagnose or prescribe."
        osm_error = next((item for item in source_errors if item.get("source") == "OpenStreetMap"), None)
        location_error = next((item for item in source_errors if item.get("source") == "Location"), None)
        if osm_error:
            reply += f" MediReach doctor profiles are shown if present. {osm_error['message']}"
        elif location_error:
            reply += f" The area could not be resolved for mapped nearby search; managed results were matched against stored address text only. {location_error['message']}"
        elif latitude is None or longitude is None:
            reply += " Share your location with the optional chat control to include nearby mapped clinician listings."
        return ({
            "reply": reply,
            "intent": "doctor_discovery",
            "response_type": "doctor_results",
            "emergency": False,
            "doctors": doctors[:5],
            "mapped_facilities": mapped_facilities[:5],
            "providers": providers[:10],
            "source_errors": source_errors,
            "actions": [{"label": "Open doctor directory", "href": "/doctors/"}],
        }, state)

    if re.search(r"\b(?:referral|refer me|refer(?:red)? to|send my details)\b", text):
        return ({
            "reply": "I can prepare a local demonstration referral request. It is not sent to a hospital; review and submit the form to save it in MediReach.",
            "intent": "referral_request",
            "response_type": "referral_action",
            "emergency": False,
            "actions": [{"label": "Prepare a referral request", "href": "/referrals/new/"}],
        }, state)

    if is_historical_only(message):
        return ({
            "reply": "I understand you are describing a past symptom. I will not treat it as current. If it is happening now or has returned, tell me what you are experiencing.",
            "intent": "historical_symptom_context",
            "response_type": "assistant_message",
            "emergency": False,
            "actions": [],
        }, state)
    flow_result = handle_symptom_flow(message, state)
    if flow_result:
        return flow_result

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
    if reply == FALLBACK:
        if re.search(r"\b(?:medicine|medication|drug|dosage|dose|milligram|mg|diagnos(?:e|is)|what (?:do|disease|condition) i have|appointment|booking|verified|verification|open now|accepting patients|emergency services)\b", text):
            return ({"reply": reply, "intent": "general_health", "response_type": "assistant_message",
                     "emergency": False, "response_mode": "deterministic_fallback",
                     "fallback_notice": "For personal medical or provider-specific decisions, contact a qualified professional or use the relevant directory."}, next_state)
        ai_reply, _ai_status = generate_general_reply(message)
        if ai_reply:
            return ({"reply": ai_reply, "intent": "general_health", "response_type": "assistant_message",
                     "emergency": False, "response_mode": "local_ai", "fallback_notice": "Local AI response; general information only."}, next_state)
        return ({"reply": reply, "intent": "general_health", "response_type": "assistant_message",
                 "emergency": False, "response_mode": "deterministic_fallback",
                 "fallback_notice": "Local AI is unavailable or not configured. Showing deterministic guidance."}, next_state)
    return ({"reply": reply, "intent": "general_health", "response_type": "assistant_message", "emergency": False}, next_state)
