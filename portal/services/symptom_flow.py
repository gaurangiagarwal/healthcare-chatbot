"""Deterministic, one-question-at-a-time collection of patient-reported context."""
import re

from portal.chatbot import (
    _general_guidance,
    detect_negated_symptoms,
    detect_symptoms,
    parse_duration,
)


_HEALTH_CONCERN = re.compile(
    r"\b(?:symptom|symptoms|health concern|not feeling well|feel unwell|"
    r"i feel|i'm experiencing|i am experiencing|pain|ache|nausea|"
    r"vomit|rash|dizz|diarrh|constipat|weakness|swollen|itch|burning|"
    r"sore throat|fatigue|tired|unwell)\b",
    re.I,
)
_HISTORICAL_CONCERN = re.compile(
    r"\b(?:history of|used to have|previously had|had .{0,40} (?:last week|last year|last month|years ago)|"
    r"resolved|recovered from|no longer have)\b",
    re.I,
)
_CURRENT_CONTEXT = re.compile(r"\b(?:now|currently|again|still|today|this morning|since yesterday|came back|returned|is back|recurred)\b", re.I)
_SEVERITY = re.compile(
    r"\b(?P<word>mild|slight|moderate|medium|severe|serious|intense|unbearable|very bad|not bad)\b|"
    r"\b(?P<score>10|[0-9])\s*(?:/\s*10|out of 10)\b",
    re.I,
)
_RELEVANT_CONTEXT = re.compile(
    r"\b(?:pregnan\w*|breastfeed\w*|diabet\w*|asthma|heart disease|"
    r"immune[- ]suppressed|immunocompromised|cancer|kidney disease|"
    r"liver disease|recent surgery|serious medical condition)\b",
    re.I,
)
_STOP_FLOW = re.compile(
    r"^\s*(?:stop(?: asking| symptom (?:questions|flow))?|cancel|exit|quit|end (?:this|the) (?:flow|questions?)|"
    r"return to (?:the )?(?:normal|general) assistant|back to the assistant)\s*[.! ]*$",
    re.I,
)


def is_stop_request(message):
    return bool(_STOP_FLOW.fullmatch(message or ""))


def is_historical_only(message):
    text = str(message or "")
    return bool(detect_symptoms(text) and _HISTORICAL_CONCERN.search(text) and not _CURRENT_CONTEXT.search(text))


def _severity(message):
    if re.search(r"\b(?:not|isn't|is not|never)\s+(?:very\s+)?severe\b", message, re.I):
        return {"reported": "not severe", "category": "unspecified"}
    match = _SEVERITY.search(message)
    if not match:
        return None
    if match.group("score") is not None:
        score = int(match.group("score"))
        category = "mild" if score <= 3 else "moderate" if score <= 6 else "severe"
        return {"reported": match.group(0), "category": category}
    word = match.group("word").casefold()
    if word in {"mild", "slight", "not bad"}:
        category = "mild"
    elif word in {"moderate", "medium"}:
        category = "moderate"
    else:
        category = "severe"
    return {"reported": match.group(0), "category": category}


def _onset(message):
    parsed = parse_duration(message)
    if parsed:
        return parsed
    if re.search(r"\b(?:today|this morning|this afternoon|last night|a few days ago|not sure|don't know)\b", message, re.I):
        return message.strip()[:200]
    return None


def _concern(message, symptoms):
    if symptoms:
        return ", ".join(symptoms)
    if not _HEALTH_CONCERN.search(message):
        return None
    if re.search(r"\b(?:symptoms|health concern)\b", message, re.I) and not re.search(
        r"\b(?:i feel|i'm experiencing|i am experiencing|pain|ache|rash|nausea|vomit|dizz|fever|cough|headache|sore throat)\b",
        message,
        re.I,
    ):
        return None
    cleaned = re.sub(
        r"^\s*(?:i have|i'm having|i am having|i feel|i'm experiencing|i am experiencing|my concern is)\s+",
        "", message.strip(), flags=re.I,
    ).strip(" .,!?")
    return cleaned[:240] or message.strip()[:240]


def _question(flow):
    if not flow.get("main_concern"):
        flow["last_question"] = "main_concern"
        flow["stage"] = "awaiting_concern"
        return "What symptom or health concern would you like to discuss?"
    if not flow.get("onset"):
        flow["last_question"] = "onset"
        flow["stage"] = "awaiting_onset"
        return "When did it start?"
    if not flow.get("severity"):
        flow["last_question"] = "severity"
        flow["stage"] = "awaiting_severity"
        return "How severe is it right now: mild, moderate, or severe?"
    if flow.get("associated_symptoms") is None:
        flow["last_question"] = "associated_symptoms"
        flow["stage"] = "awaiting_associated_symptoms"
        return "Are you noticing any other symptoms?"
    if flow.get("severity", {}).get("category") == "severe" and flow.get("medical_context") is None:
        flow["last_question"] = "medical_context"
        flow["stage"] = "awaiting_medical_context"
        return "Is there a significant existing condition, pregnancy, or recent surgery that may be relevant? You can say none."
    return None


def _guidance(flow):
    symptom_keys = flow.get("symptoms") or []
    advice = _general_guidance(symptom_keys)
    concern = flow.get("main_concern") or "your concern"
    onset = flow.get("onset") or "not stated"
    severity = flow.get("severity", {}).get("reported", "not stated")
    associated = flow.get("associated_symptoms") or "not stated"
    text = (
        f"You reported {concern}; it started {onset}; severity reported: {severity}; "
        f"other symptoms reported: {associated}. {advice} "
    )
    if flow.get("severity", {}).get("category") == "severe":
        text += "Because you describe it as severe, seek prompt professional care."
    text += " I cannot determine the cause or diagnose you; this is general information, not a substitute for a clinician."
    return text


def handle_symptom_flow(message, state=None):
    """Return a structured response/state, or None when the message is not a symptom flow."""
    state = dict(state or {})
    flow = state.get("health_flow")
    active = isinstance(flow, dict) and flow.get("active") is True
    text = " ".join(str(message or "").split())
    detected = detect_symptoms(text)

    if not active:
        if is_historical_only(text):
            return None
        if not detected and detect_negated_symptoms(text):
            return None
        concern = _concern(text, detected)
        if concern is None and not re.search(r"\b(?:help me understand these symptoms|tell me about my symptoms|discuss my symptoms)\b", text, re.I):
            return None
        flow = {
            "active": True,
            "main_concern": concern,
            "symptoms": detected,
            "onset": _onset(text),
            "severity": _severity(text),
            "associated_symptoms": None,
            "medical_context": None,
            "last_question": None,
            "stage": "collecting",
        }
        context = _RELEVANT_CONTEXT.search(text)
        if context:
            flow["medical_context"] = context.group(0)
    else:
        question = flow.get("last_question")
        if question == "main_concern":
            flow["main_concern"] = text[:240]
            flow["symptoms"] = detected
        elif question == "onset":
            flow["onset"] = _onset(text) or text[:200] or "Not stated"
            flow["severity"] = flow.get("severity") or _severity(text)
        elif question == "severity":
            flow["severity"] = _severity(text) or {"reported": text[:100] or "Not stated", "category": "unspecified"}
        elif question == "associated_symptoms":
            if re.fullmatch(r"\s*(?:no|nope|none|nothing else|not really|no other symptoms|just that)\s*[.! ]*", text, re.I):
                flow["associated_symptoms"] = "None reported"
            else:
                flow["associated_symptoms"] = text[:240] or "Not stated"
        elif question == "medical_context":
            flow["medical_context"] = text[:240] or "Not stated"
        # Capture additional user-reported symptoms/context instead of asking for them again.
        if question != "main_concern" and detected:
            additions = [item for item in detected if item not in flow.get("symptoms", [])]
            if additions and flow.get("associated_symptoms") is None:
                flow["associated_symptoms"] = ", ".join(additions)
        if flow.get("medical_context") is None:
            context = _RELEVANT_CONTEXT.search(text)
            if context:
                flow["medical_context"] = context.group(0)

    next_question = _question(flow)
    state["health_flow"] = flow
    # Keep the legacy conversation-state key in sync for existing history and clients.
    state["symptoms"] = list(flow.get("symptoms") or [])
    if next_question:
        reply = f"I can help organize what you report. {next_question}"
        return ({
            "reply": reply,
            "intent": "structured_symptom_followup",
            "response_type": "symptom_followup",
            "emergency": False,
            "flow_stage": flow["stage"],
            "question": next_question,
            "flow_active": True,
            "actions": [],
        }, state)

    flow["active"] = False
    flow["stage"] = "complete"
    flow["last_question"] = None
    reply = _guidance(flow)
    return ({
        "reply": reply,
        "intent": "structured_symptom_summary",
        "response_type": "symptom_summary",
        "emergency": False,
        "symptom_summary": {
            "main_concern": flow["main_concern"],
            "onset": flow["onset"],
            "severity": flow["severity"],
            "associated_symptoms": flow["associated_symptoms"],
            "medical_context": flow["medical_context"],
        },
        "flow_active": False,
        "actions": [],
    }, state)
