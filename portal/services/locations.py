"""Explicit, cached resolution of Indian place queries to map coordinates."""
import json
import os
import threading
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings


DEFAULT_GEOCODER_URL = "https://nominatim.openstreetmap.org/search"
REQUEST_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_NEGATIVE_TTL_SECONDS = 10 * 60
CACHE_ERROR_TTL_SECONDS = 30
MAX_CACHE_ENTRIES = 512
_cache = {}
_error_cache = {}
_lock = threading.Lock()
_RATE_LIMIT_STATE = Path(tempfile.gettempdir()) / "medireach-nominatim-rate-limit-v1.lock"
_rate_limit_until = 0.0


class LocationResolutionError(Exception):
    """Safe error for a missing or unavailable place lookup."""

    def __init__(self, message, *, reason="unavailable", status_code=None, retry_after=None):
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code
        self.retry_after = retry_after


def _throttle_request():
    """Serialize Nominatim requests across workers sharing this host."""
    with _lock:
        if _rate_limit_until > time.time():
            remaining = max(1, int(_rate_limit_until - time.time()))
            raise LocationResolutionError(
                f"Location search was rate-limited. Please wait about {remaining} seconds before trying again.",
                reason="rate_limited", status_code=429, retry_after=remaining,
            )
        try:
            with _RATE_LIMIT_STATE.open("a+b") as handle:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0, os.SEEK_END)
                    if handle.tell() == 0:
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.seek(1)
                    raw = handle.read(64)
                    try:
                        last_request = float(raw.decode("ascii") or "0")
                    except (UnicodeError, ValueError):
                        last_request = 0.0
                    delay = 1.0 - (time.time() - last_request)
                    if delay > 0:
                        time.sleep(delay)
                    now = time.time()
                    handle.seek(0)
                    handle.truncate()
                    handle.write(b"0" + f"{now:.6f}".encode("ascii"))
                    handle.flush()
                finally:
                    if os.name == "nt":
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            raise LocationResolutionError("Location search cannot meet the service rate limit right now.") from exc


def _endpoint():
    value = os.getenv("MEDIREACH_GEOCODER_URL", DEFAULT_GEOCODER_URL).strip()
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise LocationResolutionError("Location search is not configured safely.")
    return value


def normalize_location(value):
    if not isinstance(value, str):
        raise ValueError("Enter a city, area, or PIN code.")
    normalized = " ".join(value.split()).strip(" ,")
    if not normalized or len(normalized) > 120 or any(ord(char) < 32 for char in normalized):
        raise ValueError("Enter a valid city, area, or PIN code.")
    if normalized.isdecimal() and (len(normalized) != 6 or normalized[0] == "0"):
        raise ValueError("Enter a valid six-digit Indian PIN code.")
    return normalized


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


def _valid_point(item):
    try:
        latitude, longitude = float(item["lat"]), float(item["lon"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {"latitude": latitude, "longitude": longitude, "display_name": str(item.get("display_name", ""))[:300]}


def resolve_location(value):
    """Resolve one user-submitted Indian area/city/PIN; no autocomplete."""
    try:
        query = normalize_location(value)
    except ValueError as exc:
        raise LocationResolutionError(str(exc), reason="invalid_query") from exc
    if getattr(settings, "RUNNING_TESTS", False):
        raise LocationResolutionError("External location lookup is disabled during tests.")
    key = (_endpoint(), query.casefold())
    now = time.monotonic()
    with _lock:
        cached_error = _error_cache.get(key)
        if cached_error and cached_error[0] > now:
            raise LocationResolutionError(
                cached_error[1], reason=cached_error[2], status_code=cached_error[3], retry_after=cached_error[4]
            )
        if cached_error:
            _error_cache.pop(key, None)
        cached = _cache.get(key)
        if cached and cached[0] > now:
            if cached[1] is None:
                raise LocationResolutionError(
                    "That area could not be located. Check the spelling or try a nearby city.", reason="not_found"
                )
            return dict(cached[1])
        if cached:
            _cache.pop(key, None)

    _throttle_request()

    params = urlencode({"q": query, "format": "jsonv2", "countrycodes": "in", "limit": 1})
    request = Request(
        f"{key[0]}?{params}",
        headers={"User-Agent": "MediReach/1.0 (user-triggered Indian location search)", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read(128 * 1024)
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise LocationResolutionError("Location search returned an unreadable response.", reason="malformed_response") from exc
        if not isinstance(decoded, list):
            raise LocationResolutionError("Location search returned an unexpected response.", reason="malformed_response")
        point = _valid_point(decoded[0]) if decoded else None
    except LocationResolutionError:
        raise
    except HTTPError as exc:
        retry_after = _retry_after_seconds(exc.headers.get("Retry-After") if exc.headers else None)
        if exc.code == 429:
            message = "Location search was rate-limited. Please wait before trying again."
            error = LocationResolutionError(message, reason="rate_limited", status_code=429, retry_after=retry_after)
            global _rate_limit_until
            _rate_limit_until = time.time() + max(CACHE_ERROR_TTL_SECONDS, retry_after or 0)
            with _lock:
                for old_key, (expires, *_details) in list(_error_cache.items()):
                    if expires <= time.monotonic():
                        _error_cache.pop(old_key, None)
                if len(_error_cache) >= MAX_CACHE_ENTRIES:
                    _error_cache.pop(next(iter(_error_cache)))
                _error_cache[key] = (time.monotonic() + max(CACHE_ERROR_TTL_SECONDS, retry_after or 0), message, error.reason, error.status_code, error.retry_after)
            raise error from exc
        if exc.code == 403:
            raise LocationResolutionError("The location service refused this request. Try again later.", reason="access_refused", status_code=403) from exc
        if exc.code in {400, 404, 422}:
            raise LocationResolutionError("That area could not be located. Check the spelling or try a nearby city.", reason="not_found", status_code=exc.code) from exc
        raise LocationResolutionError("Location service is temporarily unavailable. Try again shortly.", reason="http_error", status_code=exc.code) from exc
    except (TimeoutError, OSError) as exc:
        raise LocationResolutionError("Location search timed out. Please try again shortly.", reason="timeout") from exc
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, OSError)):
            raise LocationResolutionError("Location search timed out. Please try again shortly.", reason="timeout") from exc
        raise LocationResolutionError("Location service is temporarily unavailable. Check your connection and try again.", reason="network_error") from exc
    except (ValueError, UnicodeError) as exc:
        raise LocationResolutionError("Location search returned an unreadable response.", reason="malformed_response") from exc
    if decoded and point is None:
        raise LocationResolutionError("Location search returned invalid coordinates.", reason="invalid_coordinates")
    with _lock:
        if len(_cache) >= MAX_CACHE_ENTRIES:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic() + (CACHE_TTL_SECONDS if point else CACHE_NEGATIVE_TTL_SECONDS), point)
    if point is None:
        raise LocationResolutionError("That area could not be located. Check the spelling or try a nearby city.", reason="not_found")
    return dict(point)
