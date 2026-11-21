"""Educational rule-based replies with conversation-local symptom context."""
import re

# These broad ranges are configurable guardrails for parsing body-temperature
# readings, not clinical thresholds. Values outside them are never converted.
TEMPERATURE_PLAUSIBLE_RANGES = {"F": (80.0, 115.0), "C": (26.0, 46.0)}
DEGREE = chr(176)

EMERGENCY_PATTERNS = {
    "severe_chest_pain": r"\bsevere chest pain\b|\bchest pain\b",
    "breathing_difficulty": r"\b(?:can't|cannot|unable to) breathe\b|\bbreathing difficulty\b|\bdifficulty breathing\b|\bshortness of breath\b",
    "unconsciousness": r"\bunconscious\b",
    "severe_bleeding": r"\bsevere bleeding\b",
    "stroke_warning": r"\bstroke\b",
    "suicidal_crisis": r"\bsuicidal\b",
    "confusion": r"\bconfus(?:ed|ion)\b",
    "sudden_severe_headache": r"\bsudden severe headache\b",
    "severe_headache_neck_stiffness": r"\bsevere headache\b.*\bneck stiffness\b|\bneck stiffness\b.*\bsevere headache\b",
}

SYMPTOMS = {
    "fever": (r"\bfever\b", r"\bfebrile\b"),
    "cough": (r"\bcough(?:ing)?\b",),
    "headache": (r"\bheadaches?\b",),
    "stomach pain": (r"\bstomach pain\b", r"\bstomach ache\b", r"\bstomachache\b", r"\babdominal pain\b", r"\bstomach cramps?\b"),
    "sore throat": (r"\bsore throat\b", r"\bthroat pain\b"),
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
NUMBER = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
DURATION_RE = re.compile(
    rf"\b(?:since\s+(?:this\s+)?morning|since\s+yesterday|since\s+last\s+night|"
    rf"for\s+{NUMBER}\s+(?:hours?|days?|weeks?))\b", re.I
)
UNIT_PATTERN = r"(?:fahrenheit|celsius|f\b|c\b)"
TEMPERATURE_WITH_UNIT_RE = re.compile(
    rf"\b(?P<value>\d{{2,3}}(?:\.\d+)?)\s*(?:{DEGREE}\s*)?(?:degrees?\s*)?"
    rf"(?P<unit>{UNIT_PATTERN})", re.I
)
TEMPERATURE_MARKER_RE = re.compile(
    r"\b(?:my\s+)?(?:body\s+)?(?:temperature|temp|reading)\s*(?:is|was|of|:|=)?\s*"
    r"(?P<value>\d{2,3}(?:\.\d+)?)\b", re.I
)
UNIT_ONLY_RE = re.compile(r"\b(fahrenheit|celsius|f|c)\b", re.I)
NEGATION_RE = re.compile(r"\b(?:no|not|don't|do not|doesn't|does not|without|deny|denies|never)\b", re.I)
FALLBACK = (
    "I don't have reliable guidance for that question. Please contact a qualified "
    "healthcare professional. I can share general information about fever, cough, "
    "headache, stomach pain, or sore throat."
)


def _is_negated(text, start):
    prefix = re.split(r"[,;.!?]", text[:start])[-1]
    prefix = re.split(r"\b(?:but|however|although|except)\b", prefix)[-1]
    words = prefix.lower().split()
    recent = " ".join(words[-5:])
    return any(NEGATION_RE.fullmatch(word.strip("'")) for word in words[-5:]) or "don't" in recent or "do not" in recent


def detect_symptoms(message):
    """Return supported, positively stated symptoms in stable display order."""
    text = message.lower().replace(chr(8217), "'")
    just_match = re.search(r"\bjust\s+(.+)$", text)
    positive_tail = just_match.start(1) if just_match else None
    detected = []
    for symptom, patterns in SYMPTOMS.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match and (match.start() >= positive_tail if positive_tail is not None else not _is_negated(text, match.start())):
                detected.append(symptom)
                break
    return detected


def detect_negated_symptoms(message):
    text = message.lower().replace(chr(8217), "'")
    found = []
    for symptom, patterns in SYMPTOMS.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match and _is_negated(text, match.start()):
                found.append(symptom)
                break
    return found


def parse_duration(message):
    match = DURATION_RE.search(message)
    if not match:
        return None
    value = " ".join(match.group(0).lower().split())
    value = re.sub(r"^since morning$", "since this morning", value)
    for word, number in NUMBER_WORDS.items():
        value = re.sub(rf"\b{word}\b", str(number), value)
    return value


def _temperature_result(value, unit):
    """Validate in the stated unit; never convert an implausible value."""
    low, high = TEMPERATURE_PLAUSIBLE_RANGES[unit]
    plausible = low <= value <= high
    if not plausible:
        return {"value": value, "unit": unit, "plausible": False}
    result = {"value": value, "unit": unit}
    if unit == "F":
        result["celsius"] = round((value - 32) * 5 / 9, 1)
    else:
        result["fahrenheit"] = round(value * 9 / 5 + 32, 1)
    return result


def parse_temperature(message, allow_unitless=True):
    """Parse a numeric reading, retaining an absent unit as unknown."""
    match = TEMPERATURE_WITH_UNIT_RE.search(message)
    if match:
        unit_text = match.group("unit").lower()
        unit = "C" if unit_text.startswith("c") else "F"
        return _temperature_result(float(match.group("value")), unit)

    marker = TEMPERATURE_MARKER_RE.search(message)
    if marker:
        return {"value": float(marker.group("value")), "unit": None, "plausible": None}

    if allow_unitless:
        # A bare number is only considered a temperature when the surrounding
        # conversation is asking for a reading. Exclude duration quantities.
        duration_match = DURATION_RE.search(message)
        candidates = list(re.finditer(r"\b(?P<value>\d{2,3}(?:\.\d+)?)\b", message))
        candidates = [candidate for candidate in candidates if not duration_match or not (duration_match.start() <= candidate.start() < duration_match.end())]
        if candidates:
            return {"value": float(candidates[-1].group("value")), "unit": None, "plausible": None}
    return None


def parse_temperature_unit(message):
    match = UNIT_ONLY_RE.search(message)
    if not match:
        return None
    return "C" if match.group(1).lower().startswith("c") else "F"


def _empty_state():
    return {
        "symptoms": [],
        "duration": None,
        "temperature": None,
        "reported_temperature": None,
        "temperature_unit": None,
        "last_question": None,
        "pending_information": [],
        "emergency_warning_signs": [],
        "stage": "idle",
    }


def _emergency_warning_signs(message):
    text = message.lower().replace(chr(8217), "'")
    signs = []
    for name, pattern in EMERGENCY_PATTERNS.items():
        match = re.search(pattern, text, re.I)
        if match and not _is_negated(text, match.start()):
            signs.append(name)
    return signs


def _temperature_text(temperature):
    degree = DEGREE
    if temperature["unit"] == "F":
        return f"{temperature['value']:g}{degree}F is approximately {temperature['celsius']:.1f}{degree}C"
    return f"{temperature['value']:g}{degree}C (approximately {temperature['fahrenheit']:.1f}{degree}F)"


def _general_guidance(symptoms):
    if "fever" in symptoms:
        guidance = "Rest, drink fluids, and monitor symptoms. Contact a healthcare professional if symptoms are severe, worsening, persistent, or concerning."
    elif "cough" in symptoms:
        guidance = "Rest and fluids may help. Contact a healthcare professional for a persistent or worsening cough, blood, or concerns."
    elif "headache" in symptoms:
        guidance = "Rest, hydration, and a quiet environment may help. Contact a healthcare professional if the headache is severe, worsening, persistent, or concerning."
    elif "stomach pain" in symptoms:
        guidance = "Sip fluids and monitor symptoms. Severe or worsening pain, fainting, persistent vomiting, or blood needs urgent medical attention."
    elif "sore throat" in symptoms:
        guidance = "Warm fluids and rest may soothe a sore throat. Contact a healthcare professional for trouble swallowing, worsening symptoms, or concerns."
    else:
        guidance = "Rest, fluids, and monitoring symptoms may help. Contact a qualified healthcare professional if you are concerned."
    return guidance + " Seek urgent help for severe chest pain, difficulty breathing, confusion, or severe headache with neck stiffness."


def _symptom_names(symptoms):
    if len(symptoms) == 1:
        return symptoms[0]
    if len(symptoms) == 2:
        return f"{symptoms[0]} and {symptoms[1]}"
    return ", ".join(symptoms[:-1]) + f", and {symptoms[-1]}"


def _implausible_temperature_reply(value, unit):
    degree = DEGREE
    return (
        f"A body temperature of {value:g}{degree}{unit} is not a plausible human body-temperature reading. "
        f"Please check your thermometer and confirm whether you meant {value:g}{degree}F or another value. "
        "If you are seriously unwell, seek urgent medical care."
    )


def process_message(message, state=None):
    """Return a safe reply and updated JSON-serializable conversation state."""
    text = " ".join(message.strip().split())
    state = {**_empty_state(), **(state or {})}
    warnings = _emergency_warning_signs(text)
    if warnings:
        state["emergency_warning_signs"] = list(dict.fromkeys([*state["emergency_warning_signs"], *warnings]))
        state["pending_information"] = []
        state["last_question"] = None
        state["stage"] = "emergency"
        return (
            "This may be an emergency. Contact your local emergency number or go to the "
            "nearest emergency department now. Do not wait for a chatbot response.",
            state,
        )

    lower = text.lower()
    symptoms = detect_symptoms(text)
    negated_symptoms = detect_negated_symptoms(text)
    duration = parse_duration(text)
    waiting_for_temp = "temperature" in state["pending_information"] or state["last_question"] in {
        "duration_and_temperature", "temperature", "temperature_unit", "temperature_confirmation", "temperature_reading"
    }
    temperature = parse_temperature(text, allow_unitless=waiting_for_temp or bool(TEMPERATURE_MARKER_RE.search(text)))
    unit_only = parse_temperature_unit(text)
    no_more = bool(re.search(r"\b(?:no|nope|not really),?\s+(?:just|only)\b", lower)) or lower in {"no", "nope", "no other symptoms"}

    if symptoms:
        if state["stage"] in {"idle", "complete", "emergency"}:
            old_warnings = state["emergency_warning_signs"]
            state = _empty_state()
            state["emergency_warning_signs"] = old_warnings
        state["symptoms"] = list(dict.fromkeys([*state["symptoms"], *symptoms]))
    if duration:
        state["duration"] = duration

    if temperature:
        state["reported_temperature"] = temperature["value"]
        state["temperature_unit"] = temperature["unit"]
        state["temperature"] = temperature
    elif unit_only and state["reported_temperature"] is not None and state["temperature_unit"] is None:
        temperature = _temperature_result(state["reported_temperature"], unit_only)
        state["temperature_unit"] = unit_only
        state["temperature"] = temperature
    elif unit_only and state["stage"] == "temperature_implausible" and state["reported_temperature"] is not None:
        temperature = _temperature_result(state["reported_temperature"], unit_only)
        state["temperature_unit"] = unit_only
        state["temperature"] = temperature

    if negated_symptoms and not symptoms:
        state["symptoms"] = [symptom for symptom in state["symptoms"] if symptom not in negated_symptoms]
        if not state["symptoms"]:
            state = _empty_state()
            return "Thanks for clarifying. I won't treat that as a symptom. Tell me what general information you need.", state

    temperature = state["temperature"]
    if temperature and temperature.get("plausible") is False:
        state["emergency_warning_signs"] = list(dict.fromkeys([*state["emergency_warning_signs"], "temperature_implausible"]))
        state["pending_information"] = ["temperature_confirmation"]
        state["last_question"] = "temperature_confirmation"
        state["stage"] = "temperature_implausible"
        return _implausible_temperature_reply(temperature["value"], temperature["unit"]), state

    if state["symptoms"] and state["last_question"] == "temperature" and lower in {"yes", "yes i have", "i did", "yeah", "yep"}:
        state["pending_information"] = ["temperature_reading"]
        state["last_question"] = "temperature_reading"
        state["stage"] = "awaiting_temperature_reading"
        return "What temperature reading did you get? Please include Fahrenheit or Celsius if you know the unit.", state

    if state["symptoms"] and state["last_question"] == "temperature" and lower in {"yes", "yes i have", "i did", "yeah", "yep"}:
        state["pending_information"] = ["temperature_reading"]
        state["last_question"] = "temperature_reading"
        state["stage"] = "awaiting_temperature_reading"
        return "What temperature reading did you get? Please include Fahrenheit or Celsius if you know the unit.", state

    if not state["symptoms"]:
        state = _empty_state()
        if any(word in lower for word in ("prevent", "prevention", "healthy")):
            return "General wellness includes regular sleep, balanced meals, movement, and preventive checkups. A clinician can tailor advice to your needs.", state
        if re.search(r"\b(?:hello|hi|help)\b", lower):
            return "Hello! Tell me what general health information you are looking for. I can share safe next steps for fever, cough, headache, stomach pain, or sore throat.", state
        return FALLBACK, state

    if temperature and temperature["unit"] is None:
        state["pending_information"] = ["temperature_unit"]
        state["last_question"] = "temperature_unit"
        state["stage"] = "awaiting_temperature_unit"
        detail = f" since {state['duration'][6:]}" if state["duration"] and state["duration"].startswith("since ") else (f" {state['duration']}" if state["duration"] else "")
        summary = f"You mentioned {_symptom_names(state['symptoms'])}{detail}, with a temperature reading of {temperature['value']:g}."
        return f"{summary} Was that Fahrenheit or Celsius?", state

    if state["stage"] == "temperature_implausible" and unit_only and temperature and temperature.get("plausible"):
        # Unit correction is accepted, then the remaining pending details are handled below.
        state["stage"] = "collecting_details"

    if state["stage"] == "ask_more" and (no_more or negated_symptoms):
        state["pending_information"] = []
        state["last_question"] = None
        state["stage"] = "complete"
        return f"Thanks for clarifying. {_general_guidance(state['symptoms'])}", state

    # An unrelated message ends the pending symptom context instead of repeatedly
    # asking an old follow-up. A unit-only answer is valid only when a reading is pending.
    valid_followup = bool(symptoms or duration or temperature or (unit_only and state["reported_temperature"] is not None) or no_more or negated_symptoms)
    if not valid_followup:
        state = _empty_state()
        if any(word in lower for word in ("prevent", "prevention", "healthy")):
            return "General wellness includes regular sleep, balanced meals, movement, and preventive checkups. A clinician can tailor advice to your needs.", state
        if re.search(r"\b(?:hello|hi|help)\b", lower):
            return "Hello! Tell me what general health information you are looking for. I can share safe next steps for fever, cough, headache, stomach pain, or sore throat.", state
        return FALLBACK, state

    pending = []
    if not state["duration"]:
        pending.append("duration")
    if not state["temperature"]:
        pending.append("temperature")
    elif state["temperature_unit"] is None:
        pending.append("temperature_unit")
    state["pending_information"] = pending

    if pending:
        state["stage"] = "collecting_details"
        if pending == ["duration", "temperature"]:
            state["last_question"] = "duration_and_temperature"
            return "How long have you had these symptoms? Have you measured your temperature?", state
        if pending == ["duration"]:
            state["last_question"] = "duration"
            return "How long have you had these symptoms?", state
        if pending == ["temperature"]:
            state["last_question"] = "temperature"
            return "Have you measured your temperature?", state
        state["last_question"] = "temperature_unit"
        state["stage"] = "awaiting_temperature_unit"
        return "Was that temperature in Fahrenheit or Celsius?", state

    if state["stage"] != "ask_more" and state["stage"] != "complete":
        summary = f"You mentioned {_symptom_names(state['symptoms'])}"
        if state["duration"]:
            summary += f" {state['duration']}"
        if temperature:
            summary += f", with a temperature reading of {_temperature_text(temperature)}"
        state["pending_information"] = ["other_symptoms"]
        state["last_question"] = "other_symptoms"
        state["stage"] = "ask_more"
        return f"{summary}. {_general_guidance(state['symptoms'])} Are you experiencing any other symptoms?", state

    if symptoms:
        state["pending_information"] = ["other_symptoms"]
        state["last_question"] = "other_symptoms"
        return f"Thanks for letting me know. {_general_guidance(state['symptoms'])} Are you experiencing any other symptoms?", state

    return f"{_general_guidance(state['symptoms'])}", state


def reply(message):
    """Backward-compatible stateless helper for existing callers and tests."""
    return process_message(message, {})[0]
