"""Deterministic emergency screening; intentionally independent of any AI service."""
import re


EMERGENCY_RULES = {
    "chest_pain": (r"\b(?:severe )?chest (?:pain|pressure|tightness)\b", "cardiac"),
    "breathing_difficulty": (r"\b(?:severe )?(?:difficulty breathing|breathing difficulty|can't breathe|cannot breathe|shortness of breath|gasping)\b", None),
    "stroke_warning": (r"\b(?:stroke|face droop(?:ing)?|slurred speech|sudden one[- ]sided weakness)\b", "stroke"),
    "severe_bleeding": (r"\b(?:severe|heavy|uncontrolled|spurting) bleeding\b|\bbleeding won't stop\b", "bleeding"),
    "unconsciousness": (r"\b(?:unconscious|unresponsive|passed out and won't wake)\b", None),
    "severe_allergic_reaction": (r"\b(?:anaphylaxis|throat swelling|tongue swelling|severe allergic reaction)\b", "allergic-reaction"),
    "severe_headache_with_neck_stiffness": (r"\b(?:severe|worst) headache\b.{0,50}\bneck stiffness\b|\bneck stiffness\b.{0,50}\b(?:severe|worst) headache\b", None),
    "seizure": (r"\b(?:seizure|convulsion|fitting)\b", "seizures"),
}


def _negated(text, start):
    prefix = re.split(r"[,;.!?]", text[:start])[-1]
    prefix = re.split(r"\b(?:but|however|although|except)\b", prefix)[-1]
    return bool(re.search(r"\b(?:no|not|don't|do not|doesn't|without|denies)\b", prefix[-50:], re.I))


def assess_emergency(message):
    """Return explicit warning keys and a guide slug; never estimates safety."""
    text = message.lower().replace(chr(8217), "'")
    matches = []
    guide = None
    for key, (pattern, guide_slug) in EMERGENCY_RULES.items():
        match = re.search(pattern, text, re.I)
        if match and not _negated(text, match.start()):
            matches.append(key)
            guide = guide_slug or guide
    return {"is_emergency": bool(matches), "warning_signs": matches, "guide": guide}
