"""Optional, local-only Ollama text assistance for non-safety chat questions."""
import ipaddress
import json
import os
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


MAX_OUTPUT_CHARS = 1800
_UNSAFE_OUTPUT = re.compile(
    r"\b(?:you have|you are suffering from|you may have|likely|probably|suggests|"
    r"consistent with|could be|might be|may be|caused by|diagnos(?:e|ed|is)|prescrib\w*|"
    r"take\s+(?:\d|one|two|three|a|an)|dosage|dose of|\d+(?:\.\d+)?\s*(?:mg|mcg|ml)\b|"
    r"\b(?:tablet|capsule|medicine|medication|drug|pill|antibiotic|antihistamine|"
    r"analgesic|ibuprofen|paracetamol|acetaminophen|aspirin|antacid|inhaler|steroid)\b|"
    r"\bdr\.?\s+[a-z]+\b|(?:contact|visit) (?:the )?(?:hospital|clinic) named\b|"
    r"emergency services (?:have been|were) contacted|appointment (?:is|has been) confirmed|"
    r"verified provider|accepting patients|open now)\b",
    re.I,
)


def _configuration():
    base_url = os.getenv("OLLAMA_BASE_URL", "").strip()
    model = os.getenv("OLLAMA_MODEL", "").strip()
    if not base_url or not model:
        return None
    try:
        parsed = urlsplit(base_url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    hostname = parsed.hostname.casefold()
    if hostname != "localhost":
        try:
            if not ipaddress.ip_address(hostname).is_loopback:
                return None
        except ValueError:
            return None
    timeout = 8.0
    try:
        timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "8"))
    except (TypeError, ValueError):
        pass
    return base_url.rstrip("/"), model, min(20.0, max(1.0, timeout))


def _validate_output(value):
    if not isinstance(value, str):
        return None
    value = " ".join(value.split()).strip()
    if not value or len(value) > MAX_OUTPUT_CHARS or _UNSAFE_OUTPUT.search(value):
        return None
    if "```" in value or re.search(r"\b(?:ignore (?:all )?(?:previous|safety)|system prompt|api key|secret key)\b", value, re.I):
        return None
    return value


def generate_general_reply(user_message):
    """Return a checked local reply, or None when unavailable/unsafe.

    Only the current general question is sent. Emergency decisions, conversation
    state, coordinates, provider facts and appointment/referral data never enter
    this request. The returned text remains untrusted plain text.
    """
    configuration = _configuration()
    if not configuration:
        return None, "not_configured"
    base_url, model, timeout = configuration
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": (
                "Give cautious, general health education only. Do not diagnose, prescribe, "
                "recommend medicine doses, interpret emergencies, make provider or booking "
                "claims, or replace a clinician. If the user may have urgent symptoms, tell "
                "them to contact emergency services or a qualified clinician. Be concise."
            )},
            {"role": "user", "content": str(user_message)[:2000]},
        ],
    }
    request = Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(128 * 1024)
        decoded = json.loads(raw.decode("utf-8"))
        answer = _validate_output(decoded.get("message", {}).get("content") if isinstance(decoded, dict) else None)
        if answer is None:
            return None, "malformed_or_unsafe"
        return answer + "\n\nGeneral information only; this is not a substitute for a clinician.", "ok"
    except (HTTPError, URLError, TimeoutError, socket.timeout, OSError, ValueError, UnicodeError):
        return None, "unavailable"
