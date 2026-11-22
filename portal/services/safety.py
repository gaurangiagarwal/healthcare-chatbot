"""Conservative, deterministic emergency warning screen.

This is a text warning, not a diagnosis or a way to rule out an emergency.
Warning categories follow public emergency guidance from India's Ministry of
Home Affairs (112 ERSS), the NHS ambulance services, and CDC stroke guidance:

* https://www.mha.gov.in/emergency-response-support-system-erss
* https://www.londonambulance.nhs.uk/our-services/emergency-care/calling-999/
* https://www.cdc.gov/stroke/signs-symptoms/
* https://www.nhs.uk/symptoms/confusion/
* https://www.nhs.uk/symptoms/headaches/
"""
import re


EMERGENCY_RULES = {
    "chest_pain": (
        r"\b(?:severe\s+)?chest\s+(?:pain|pressure|tightness)\b|"
        r"\b(?:heart attack|heart-attack)\b",
        "cardiac",
    ),
    "breathing_difficulty": (
        r"\b(?:difficulty breathing|breathing difficulty|shortness of breath|"
        r"breathless|gasping|can't breathe|cannot breathe|can't catch (?:(?:my|his|her|their) )?breath|"
        r"cannot catch (?:(?:my|his|her|their) )?breath|unable to breathe|"
        r"trouble breathing|struggling to breathe|no longer breathing|(?:isn't|not) breathing)\b",
        None,
    ),
    "stroke_warning": (
        r"\b(?:face (?:is )?droop(?:ing)?|one[- ]sided (?:weakness|numbness)|"
        r"weakness on (?:one|1) side|numbness on (?:one|1) side|"
        r"slurred speech|trouble speaking|difficulty speaking|"
        r"sudden (?:trouble walking|loss of balance|vision loss)|"
        r"(?:having|had|suspected) a stroke|stroke symptoms?)\b",
        "stroke",
    ),
    "severe_bleeding": (
        r"\b(?:severe|heavy|uncontrolled|spurting|lots of) bleeding\b|"
        r"\bbleeding (?:won't|will not|doesn't|does not) stop\b|"
        r"\b(?:losing|lost) a lot of blood\b",
        "bleeding",
    ),
    "seizure": (
        r"\b(?:seiz(?:ure|ing)|convulsion|convulsing|fitting)\b",
        "seizures",
    ),
    "severe_allergic_reaction": (
        r"\b(?:anaphylaxis|anaphylactic|severe allergic reaction|"
        r"(?:throat|tongue) (?:is )?swelling|"
        r"allergic reaction with (?:throat|tongue|lip|face) swelling|"
        r"(?:throat|tongue|lip) (?:is )?swelling (?:after|from) (?:an? )?allerg(?:y|ic reaction)|"
        r"allergic reaction.{0,60}(?:swelling|difficulty breathing|trouble breathing))\b",
        "allergic-reaction",
    ),
    "unconsciousness": (
        r"\b(?:unconscious|unresponsive|lost consciousness|loss of consciousness|"
        r"passed out|fainted|fainting|not waking up)\b",
        None,
    ),
    "sudden_severe_headache": (
        r"\b(?:sudden|worst|extremely painful|thunderclap)[\s,]+(?:and\s+)?"
        r"(?:very\s+|extremely\s+)?severe headache\b|"
        r"\b(?:worst headache|thunderclap headache|headache.{0,35}came on suddenly)\b",
        None,
    ),
    "severe_headache_with_neck_stiffness": (
        r"\b(?:severe|worst|sudden) headache\b.{0,60}\bneck stiffness\b|"
        r"\bneck stiffness\b.{0,60}\b(?:severe|worst|sudden) headache\b",
        None,
    ),
    "severe_confusion": (
        r"\b(?:suddenly (?:became |got )?confused|sudden confusion|acute confusion|"
        r"suddenly disoriented|sudden disorientation|confused|confusion)\b",
        None,
    ),
    # Preserve an existing urgent-support scenario in the older chatbot rules.
    "suicidal_crisis": (
        r"\b(?:suicidal|want to (?:kill|hurt) myself|planning to (?:kill|hurt) myself)\b",
        None,
    ),
}

_NEGATION_CONSTRUCTION = re.compile(
    r"\b(?:no|never|without|lack(?:s|ed)?(?: of)?|den(?:y|ies|ied))"
    r"(?:\s+\w+){0,3}\s*$|"
    r"\b(?:not|don't|do not|doesn't|does not|didn't|did not|can't|cannot|can not|"
    r"isn't|is not|aren't|are not)\s+(?:currently\s+)?"
    r"(?:have|has|having|experience|experiences|experienced|experiencing|feel|feels|feeling|"
    r"be|being|show|shows|suffer|suffers|suffering)\b(?:\s+\w+){0,3}\s*$|"
    r"\b(?:not|isn't|is not|aren't|are not)\s*$",
    re.I,
)
_NEGATED_AFTER = re.compile(r"^\s*(?:is|are|was|were)?\s*(?:not present|absent|denied|ruled out|gone|resolved)\b", re.I)
_HISTORICAL = re.compile(
    r"\b(?:history of|old|past|previous|used to have|previously had|had (?:a|an)?|"
    r"last (?:week|month|year)|yesterday|earlier this week|resolved|recovered from|"
    r"\d+\s+(?:days?|weeks?|months?|years?)\s+ago|in (?:19|20)\d{2})\b",
    re.I,
)
_RECENT_EVENT = re.compile(
    r"\b(?:\d+\s+)?(?:seconds?|minutes?|hours?)\s+ago\b|"
    r"\b(?:just now|a moment ago|moments ago|recently|within the last\s+\d+\s+"
    r"(?:seconds?|minutes?|hours?))\b",
    re.I,
)
_CURRENT = re.compile(r"\b(?:now|currently|right now|again|still|ongoing|happening)\b", re.I)
_CURRENT_REFERENCE_AFTER = re.compile(
    r"^\s*(?:(?:yesterday|earlier today|last (?:night|week|month|year)|"
    r"\d+\s+(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago)\s*)?"
    r"[,;]?\s*(?:(?:and|but|yet)\s+)?(?:i|we|he|she|they)?\s*"
    r"(?:still|currently|now)\s+(?:have|has|feel|feels|am|is|are|experience|experiencing)\s+"
    r"(?:it|them|the same(?: pain| symptom)?|those symptoms|this pain|that pain)\b",
    re.I,
)
_EXPLICIT_CURRENT = re.compile(
    r"\b(?:i|we|he|she|they|someone|a person|my\s+\w+)\b.{0,100}\b"
    r"(?:am|is|are|have|has|having|experiencing|experience|feel|feels|fainted|passed out)\b"
    r".{0,100}\b(?:now|right now|currently|just now)\b",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"\b(?:what if|suppose|hypothetically|imagine|in a story|for a school|"
    r"for an assignment|if someone|if a person|if you were|would it be|"
    r"could (?:it|this|that) be|how do you recognize|how to recognize|signs of|"
    r"symptoms of|what is (?:a |an |the )?(?:stroke|seizure|convulsion|anaphylaxis|"
    r"heart attack|chest pain|severe bleeding|difficulty breathing)|"
    r"what are (?:the )?(?:signs|symptoms) of|what are (?:the )?stroke symptoms|"
    r"what does .{1,60} mean|define\s+\w+|meaning of|"
    r"explain (?:a|the) (?:stroke|seizure|anaphylaxis))\b",
    re.I,
)
_NON_MEDICAL_CONFUSION = re.compile(
    r"\bconfus(?:ed|ion)\s+(?:about|with)\b.{0,80}\b(?:use|using|navigate|"
    r"page|site|website|app|form|button|screen|feature|instructions)\b",
    re.I,
)
_CLAUSE_BREAK = re.compile(
    r"\b(?:but|however|although|except|whereas|yet|while|meanwhile|and|or)\b|[:,;.!?\n]+|[—–]",
    re.I,
)


def _context_for(text, start, end):
    """Return the clause containing a match and its preceding context."""
    left = max((match.end() for match in _CLAUSE_BREAK.finditer(text, 0, start)), default=0)
    right_match = _CLAUSE_BREAK.search(text, end)
    right = right_match.start() if right_match else len(text)
    return text[left:right].strip()


def _is_hypothetical(text):
    return bool(_HYPOTHETICAL.search(text))


def _is_current_affirmed(text, start, end):
    clause = _context_for(text, start, end)
    boundaries = list(_CLAUSE_BREAK.finditer(text, 0, start))
    clause_start = boundaries[-1].end() if boundaries else 0
    before = text[clause_start:start]
    if _is_hypothetical(clause) and not _EXPLICIT_CURRENT.search(clause) and not _RECENT_EVENT.search(clause):
        return False
    if _NEGATION_CONSTRUCTION.search(before):
        return False
    after = text[end:]
    if _NEGATED_AFTER.search(after[:40]):
        return False
    recent = bool(_RECENT_EVENT.search(clause))
    continued = bool(_CURRENT_REFERENCE_AFTER.match(after))
    if _HISTORICAL.search(clause) and not (_CURRENT.search(clause) or recent or continued):
        return False
    return True


def assess_emergency(message):
    """Return a documented warning result without diagnosing or ruling out risk.

    Signs can coexist; every affirmed match is retained. Use of a historical or
    hypothetical example is ignored when its context is clear. References to
    another person's current symptoms remain eligible for escalation.
    """
    text = str(message or "").lower().replace(chr(8217), "'")
    matches = []
    guide = None
    for key, (pattern, guide_slug) in EMERGENCY_RULES.items():
        match = next(
            (item for item in re.finditer(pattern, text, re.I)
             if _is_current_affirmed(text, item.start(), item.end())
             and not (
                 key == "severe_confusion"
                 and _NON_MEDICAL_CONFUSION.search(_context_for(text, item.start(), item.end()))
             )),
            None,
        )
        if match:
            matches.append(key)
            guide = guide_slug or guide

    is_emergency = bool(matches)
    result = {
        "is_emergency": is_emergency,
        "matched_warning_signs": matches,
        "urgency_level": "emergency" if is_emergency else "none",
        "message": (
            "A possible emergency warning sign was mentioned. Call India's emergency number 112 now. "
            "Do not wait for further chatbot questions or use this chatbot in place of emergency services."
            if is_emergency else ""
        ),
        "recommended_action": "Call 112 now" if is_emergency else "",
        "emergency_number": "112" if is_emergency else None,
        # Backward-compatible keys used by the existing assistant response.
        "warning_signs": matches,
        "guide": guide,
    }
    return result
