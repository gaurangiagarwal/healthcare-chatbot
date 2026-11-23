"""User-triggered, read-only healthcare facility discovery through Overpass."""
import json
import threading
import time
from math import isfinite
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT_SECONDS = 8
CACHE_TTL_SECONDS = 60
CACHE_MAX_ENTRIES = 64
DEFAULT_RADIUS_KM = 5
MAX_RADIUS_KM = 20

_cache = {}
_cache_lock = threading.Lock()


class FacilityDiscoveryError(Exception):
    """Safe, user-facing discovery error without request coordinates."""

    def __init__(self, message, *, reason="unavailable", status_code=None, retry_after=None):
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code
        self.retry_after = retry_after


def _retry_after_seconds(value):
    if not value:
        return None
    try:
        return max(0, min(600, int(value)))
    except (TypeError, ValueError):
        try:
            retry_at = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
            return max(0, min(600, int((retry_at - datetime.now(timezone.utc)).total_seconds())))
        except (TypeError, ValueError):
            return None


def validate_search(latitude, longitude, radius_km=DEFAULT_RADIUS_KM):
    if any(isinstance(value, bool) for value in (latitude, longitude, radius_km)):
        raise ValueError("Valid latitude, longitude, and radius are required.")
    try:
        lat, lon, radius = float(latitude), float(longitude), float(radius_km)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Valid latitude, longitude, and radius are required.")
    if not all(map(isfinite, (lat, lon, radius))) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Coordinates are outside valid latitude/longitude ranges.")
    if not 0 < radius <= MAX_RADIUS_KM:
        raise ValueError(f"Radius must be greater than zero and no more than {MAX_RADIUS_KM} km.")
    return lat, lon, radius


def _overpass_query(latitude, longitude, radius_km):
    radius_m = int(radius_km * 1000)
    # Query common amenity values and any explicitly tagged healthcare feature.
    # Ways/relations may expose their representative point as `center`.
    return (
        "[out:json][timeout:7];("
        f"node(around:{radius_m},{latitude},{longitude})[amenity~\"^(hospital|clinic|doctors|pharmacy|dentist|nursing_home)$\"];"
        f"way(around:{radius_m},{latitude},{longitude})[amenity~\"^(hospital|clinic|doctors|pharmacy|dentist|nursing_home)$\"];"
        f"relation(around:{radius_m},{latitude},{longitude})[amenity~\"^(hospital|clinic|doctors|pharmacy|dentist|nursing_home)$\"];"
        f"node(around:{radius_m},{latitude},{longitude})[healthcare];"
        f"way(around:{radius_m},{latitude},{longitude})[healthcare];"
        f"relation(around:{radius_m},{latitude},{longitude})[healthcare];"
        ");out center tags;"
    )


def _cache_key(latitude, longitude, radius_km):
    return (round(latitude, 6), round(longitude, 6), round(radius_km, 2))


def _cached_fetch(key, query):
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and cached[0] > now:
            return cached[1]
        if cached:
            _cache.pop(key, None)

    request = Request(
        OVERPASS_URL,
        data=urlencode({"data": query}).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "MediReach/1.0 (read-only healthcare facility discovery)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise FacilityDiscoveryError("The map service returned too much data. Try a smaller search radius.")
            payload = json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        retry_after = _retry_after_seconds(exc.headers.get("Retry-After") if exc.headers else None)
        if exc.code == 429:
            raise FacilityDiscoveryError(
                "OpenStreetMap facility search was rate-limited by Overpass. Please wait before retrying.",
                reason="rate_limited", status_code=429, retry_after=retry_after,
            ) from exc
        if exc.code == 504:
            raise FacilityDiscoveryError(
                "OpenStreetMap facility search timed out. Try again later or use the managed facility list.",
                reason="timeout", status_code=504,
            ) from exc
        if exc.code in {502, 503}:
            raise FacilityDiscoveryError(
                "OpenStreetMap facility search is temporarily unavailable. Managed facility results remain available.",
                reason="service_unavailable", status_code=exc.code,
            ) from exc
        raise FacilityDiscoveryError(
            "OpenStreetMap facility search could not be completed.", reason="http_error", status_code=exc.code
        ) from exc
    except TimeoutError as exc:
        raise FacilityDiscoveryError(
            "OpenStreetMap facility search timed out. Try again later or use the managed facility list.",
            reason="timeout",
        ) from exc
    except (URLError, OSError) as exc:
        raise FacilityDiscoveryError(
            "OpenStreetMap facility search is unreachable. Check your connection; managed facility results remain available.",
            reason="network_error",
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FacilityDiscoveryError("The map service returned an unreadable response.") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise FacilityDiscoveryError("The map service returned an unexpected response.")
    remark = str(payload.get("remark", "")).casefold()
    if "rate limit" in remark or "too many requests" in remark:
        raise FacilityDiscoveryError(
            "OpenStreetMap facility search was rate-limited by Overpass. Please wait before retrying.",
            reason="rate_limited",
        )
    if "timed out" in remark or "timeout" in remark:
        raise FacilityDiscoveryError(
            "OpenStreetMap facility search timed out. Try again later or use the managed facility list.",
            reason="timeout",
        )
    if "error" in remark:
        raise FacilityDiscoveryError(
            "OpenStreetMap facility search returned a service error. Managed facility results remain available.",
            reason="service_error",
        )
    with _cache_lock:
        # Evict expired entries and then the oldest inserted item if full.
        for old_key, (expires, _) in list(_cache.items()):
            if expires <= time.monotonic():
                _cache.pop(old_key, None)
        if len(_cache) >= CACHE_MAX_ENTRIES:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, payload)
    return payload


def _category(tags):
    healthcare = (tags.get("healthcare") or "").strip().lower()
    amenity = (tags.get("amenity") or "").strip().lower()
    candidate = healthcare or amenity
    aliases = {
        "doctors": "doctor", "medical_centre": "clinic", "medical_center": "clinic",
        "diagnostic_centre": "laboratory", "diagnostic_center": "laboratory",
        "blood_bank": "blood_bank", "nursing_home": "nursing_home",
    }
    return aliases.get(candidate, candidate or None)


def _safe_web_url(value):
    if not value:
        return None
    candidate = value.strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    return candidate if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password else None


def normalize_element(element):
    """Convert one Overpass element without filling absent provider data."""
    if not isinstance(element, dict) or element.get("type") not in {"node", "way", "relation"}:
        return None
    osm_id = element.get("id")
    if not isinstance(osm_id, int) or isinstance(osm_id, bool) or osm_id <= 0:
        return None
    tags = element.get("tags")
    if not isinstance(tags, dict):
        tags = {}
    point = element if element.get("type") == "node" else element.get("center", {})
    if not isinstance(point, dict):
        return None
    try:
        latitude, longitude = float(point["lat"]), float(point["lon"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if not isfinite(latitude) or not isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None

    result = {
        "osm_type": element["type"],
        "osm_id": osm_id,
        "facility_category": _category(tags),
        "latitude": latitude,
        "longitude": longitude,
        "source_name": "OpenStreetMap",
        "source_url": f"https://www.openstreetmap.org/{element['type']}/{osm_id}",
        "trust_label": "OpenStreetMap mapped — not independently verified",
    }
    if tags.get("name"):
        result["name"] = str(tags["name"])
    specialties = []
    for key in ("healthcare:speciality", "healthcare:specialty"):
        raw_specialties = tags.get(key)
        if raw_specialties:
            specialties.extend(part.strip() for part in str(raw_specialties).split(";") if part.strip())
    if specialties:
        result["specialties"] = list(dict.fromkeys(specialties))

    address = {}
    address_tags = {
        "house_number": "addr:housenumber", "street": "addr:street",
        "neighbourhood": "addr:neighbourhood", "suburb": "addr:suburb",
        "place": "addr:place", "city": "addr:city", "district": "addr:district",
        "county": "addr:county", "postcode": "addr:postcode",
        "state": "addr:state", "country": "addr:country",
    }
    for output_key, tag_key in address_tags.items():
        if tags.get(tag_key):
            address[output_key] = str(tags[tag_key])
    if address:
        result["address"] = address
    if tags.get("phone"):
        result["phone"] = str(tags["phone"])
    website = _safe_web_url(tags.get("website") or tags.get("contact:website"))
    if website:
        result["website"] = website
    return result


def discover_facilities(latitude, longitude, radius_km=DEFAULT_RADIUS_KM):
    lat, lon, radius = validate_search(latitude, longitude, radius_km)
    key = _cache_key(lat, lon, radius)
    payload = _cached_fetch(key, _overpass_query(lat, lon, radius))
    facilities = []
    seen = set()
    for element in payload["elements"]:
        facility = normalize_element(element)
        if facility is None:
            continue
        identity = (facility["osm_type"], facility["osm_id"])
        if identity in seen:
            continue
        seen.add(identity)
        facilities.append(facility)
    return facilities
