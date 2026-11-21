"""Educational, rule-based replies with conversation-local symptom context."""
import re

EMERGENCY_PATTERNS = (
    r"\bsevere chest pain\b",
    r"\bchest pain\b",
    r"\b(?:can't|cannot|unable to) breathe\b",
    r"\bbreathing difficulty\b",
    r"\bdifficulty breathing\b",
    r"\bshortness of breath\b",
    r"\bunconscious\b",
    r"\bsevere bleeding\b",
    r"\bstroke\b",
    r"\bsuicidal\b",
    r"\bconfus(?:ed|ion)\b",
    r"\bsudden severe headache\b",
    r"\bsevere headache\b.*\bneck stiffness\b|\bneck stiffness\b.*\bsevere headache\b",
)

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
TEMPERATURE_RE = re.compile(
    r"\b(?P<value>\d{2,3}(?:\.\d+)?)\s*(?:°\s*)?(?:degrees?\s*)?"
    r"(?P<unit>fahrenheit|celsius|f\b|c\b)", re.I
)
NEGATION_RE = re.compile(r"\b(?:no|not|don't|do not|doesn't|does not|without|deny|denies|never)\b", re.I)
FALLBACK = (
    "I don't have reliable guidance for that question. Please contact a qualified "
    "healthcare professional. I can share general information about fever, cough, "
    "headache, stomach pain, or sore throat."
)


def _is_negated(text, start):
    """Check for a nearby negation before a symptom without crossing punctuation."""
    prefix = re.split(r"[,;.!?]", text[:start])[-1]
    # A contrast starts a new clause: "no cough, but I have a fever".
    prefix = re.split(r"\b(?:but|however|although|except)\b", prefix)[-1]
    words = prefix.lower().split()
    return any(NEGATION_RE.fullmatch(word.strip("'’")) for word in words[-5:]) or "don't" in " ".join(words[-5:]) or "do not" in " ".join(words[-5:])


def detect_symptoms(message):
    """Return supported, positively stated symptoms in stable display order."""
    text = message.lower().replace("’", "'")
    # In "No, just fever and headache", 'no' refers to additional symptoms.
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
    text = message.lower().replace("’", "'")
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


def parse_temperature(message):
    match = TEMPERATURE_RE.search(message)
    if not match:
        return None
    value = float(match.group("value"))
    unit_text = match.group("unit").lower()
    unit = "C" if unit_text.startswith("c") else "F"
    if unit == "F":
        celsius = round((value - 32) * 5 / 9, 1)
        if not 26 <= celsius <= 46:
            return None
        return {"value": value, "unit": unit, "celsius": celsius}
    if not 26 <= value <= 46:
        return None
    fahrenheit = round(value * 9 / 5 + 32, 1)
    return {"value": value, "unit": unit, "fahrenheit": fahrenheit}


def _empty_state():
    return {"symptoms": [], "duration": None, "temperature": None, "stage": "idle"}


def _emergency(message):
    for pattern in EMERGENCY_PATTERNS:
        match = re.search(pattern, message, re.I)
        if match and not _is_negated(message.lower().replace("’", "'"), match.start()):
            return True
    return False


def _temperature_text(temperature):
    if temperature["unit"] == "F":
        return f"approximately {temperature['celsius']:.1f}°C"
    return f"{temperature['value']:g}°C (approximately {temperature['fahrenheit']:.1f}°F)"


def _general_guidance(symptoms):
    if "fever" in symptoms:
        return (
            "Rest, drink fluids, and monitor how you feel. Seek medical advice if symptoms "
            "are severe, worsening, persistent, or concerning."
        )
    if "cough" in symptoms:
        return (
            "Rest and fluids may help. Seek medical advice for breathing difficulty, blood, "
            "worsening symptoms, or a cough that persists."
        )
    if "headache" in symptoms:
        return (
            "Rest, hydration, and a quiet environment may help. Seek medical advice if it is "
            "severe, worsening, persistent, or concerning."
        )
    if "stomach pain" in symptoms:
        return (
            "Sip fluids and monitor how you feel. Severe or worsening pain, fainting, "
            "persistent vomiting, or blood needs urgent medical attention."
        )
    if "sore throat" in symptoms:
        return "Warm fluids and rest may soothe a sore throat. Seek care for trouble breathing or swallowing, worsening symptoms, or concerns."
    return "Rest, fluids, and monitoring symptoms may help. Contact a qualified healthcare professional if you are concerned."


def _symptom_names(symptoms):
    if len(symptoms) == 1:
        return symptoms[0]
    if len(symptoms) == 2:
        return f"{symptoms[0]} and {symptoms[1]}"
    return ", ".join(symptoms[:-1]) + f", and {symptoms[-1]}"


def process_message(message, state=None):
    """Return a safe reply and updated JSON-serializable per-conversation state."""
    text = " ".join(message.strip().split())
    state = {**_empty_state(), **(state or {})}
    if _emergency(text):
        return (
            "This may be an emergency. Contact your local emergency number or go to the "
            "nearest emergency department now. Do not wait for a chatbot response.",
            _empty_state(),
        )

    symptoms = detect_symptoms(text)
    duration = parse_duration(text)
    temperature = parse_temperature(text)
    lower = text.lower()
    no_more = bool(re.search(r"\b(?:no|nope|not really),?\s+(?:just|only)\b", lower)) or lower in {"no", "nope", "no other symptoms"}
    negated_symptoms = detect_negated_symptoms(text)

    if symptoms:
        if state["stage"] in {"idle", "complete"}:
            state = _empty_state()
        state["symptoms"] = list(dict.fromkeys([*state["symptoms"], *symptoms]))
    elif not duration and not temperature and negated_symptoms:
        negatives = set(negated_symptoms)
        remaining = [symptom for symptom in state["symptoms"] if symptom not in negatives]
        if not remaining:
            return "Thanks for clarifying. I won't treat that as a symptom. Tell me what you would like general information about.", _empty_state()
        state["symptoms"] = remaining

    # Only carry context into an actual follow-up answer. An unrelated query
    # should not inherit or keep asking about symptoms from an older turn.
    if state["symptoms"] and not (symptoms or duration or temperature or no_more or negated_symptoms):
        state = _empty_state()

    if state["symptoms"] and (duration or temperature):
        if duration:
            state["duration"] = duration
        if temperature:
            state["temperature"] = temperature
        state["stage"] = "collect_details"
        missing = []
        if not state["duration"]:
            missing.append("How long have you had these symptoms?")
        if not state["temperature"]:
            missing.append("Have you measured your temperature?")
        if missing:
            return " ".join(missing), state
        summary = f"You reported {_symptom_names(state['symptoms'])} {state['duration']}"
        if state["temperature"]:
            summary += f", with a reported temperature of {_temperature_text(state['temperature'])}"
        state["stage"] = "ask_more"
        return f"{summary}. {_general_guidance(state['symptoms'])} Are you experiencing any other symptoms?", state

    if state["symptoms"] and state["stage"] == "ask_more":
        if no_more or detect_negated_symptoms(text):
            state["stage"] = "complete"
            return f"Thanks for clarifying. {_general_guidance(state['symptoms'])}", state
        if symptoms:
            state["stage"] = "complete"
            return f"Thanks for letting me know. {_general_guidance(state['symptoms'])}", state

    if state["symptoms"]:
        state["stage"] = "collect_details"
        if not state["duration"] and not state["temperature"]:
            return "How long have you had these symptoms? Have you measured your temperature?", state
        if not state["duration"]:
            return "How long have you had these symptoms?", state
        if not state["temperature"]:
            return "Have you measured your temperature?", state

    # An unrelated turn ends the pending symptom context, so a later phrase such
    # as "since yesterday" cannot accidentally attach to a stale symptom.
    if any(word in lower for word in ("prevent", "prevention", "healthy")):
        return "General wellness includes regular sleep, balanced meals, movement, and preventive checkups. A clinician can tailor advice to your needs.", _empty_state()
    if re.search(r"\b(?:hello|hi|help)\b", lower):
        return "Hello! Tell me what general health information you are looking for. I can share safe next steps for fever, cough, headache, stomach pain, or sore throat.", _empty_state()
    return FALLBACK, _empty_state()


def reply(message):
    """Backward-compatible stateless helper for existing callers and unit tests."""
    return process_message(message, {})[0]
