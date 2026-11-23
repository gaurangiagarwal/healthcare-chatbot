"""Backend tools for curated aid, demo resource discovery and handovers."""
from math import asin, cos, isfinite, radians, sin, sqrt
import re
from urllib.parse import urlsplit

from django.db.models import Prefetch, Q

from django.utils import timezone

from portal.models import (
    Doctor, DoctorHospitalAffiliation, DoctorSpecialty, EmergencyContact,
    Hospital, HospitalService, ProviderContact, ProviderSourceRecord,
    ProviderVerification, Specialty,
)
from portal.services.first_aid import get_first_aid_guide, list_first_aid_guides
from portal.services.osm_facilities import FacilityDiscoveryError, MAX_RADIUS_KM, discover_facilities
from portal.services.locations import LocationResolutionError, resolve_location


SPECIALTY_SYNONYMS = {
    "cardiologist": ("cardiology", "cardiologist", "cardiac physician"),
    "cardiology": ("cardiology", "cardiologist", "cardiac physician"),
    "dermatologist": ("dermatology", "dermatologist", "skin specialist"),
    "dermatology": ("dermatology", "dermatologist", "skin specialist"),
    "dentist": ("dentist", "dentistry", "dental"),
    "dentistry": ("dentist", "dentistry", "dental"),
    "neurologist": ("neurology", "neurologist"),
    "neurology": ("neurology", "neurologist"),
    "pediatrician": ("pediatrics", "paediatrics", "pediatrician", "paediatrician"),
    "paediatrician": ("pediatrics", "paediatrics", "pediatrician", "paediatrician"),
}


def specialty_terms(value):
    normalized = " ".join((value or "").casefold().split())
    terms = SPECIALTY_SYNONYMS.get(normalized, (normalized,))
    return tuple(dict.fromkeys(term for term in terms if term))


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km, using a spherical Earth approximation."""
    lat1, lon1, lat2, lon2 = map(radians, (float(lat1), float(lon1), float(lat2), float(lon2)))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(min(1.0, max(0.0, a))))


def _valid_coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _safe_phone(value):
    candidate = str(value or "").strip()
    if not candidate or not re.fullmatch(r"\+?[0-9][0-9 ()-]{5,38}", candidate):
        return None
    digits = re.sub(r"\D", "", candidate)
    return candidate if 7 <= len(digits) <= 20 else None


def resolve_manual_location(location):
    text = (location or "").strip()
    if text.count(",") != 1:
        return None
    try:
        return _valid_coordinates(*(part.strip() for part in text.split(",", 1)))
    except (TypeError, ValueError):
        return None


def _service_status(hospital, service_type, specialty=""):
    statuses = [
        item.effective_status for item in hospital.services.all()
        if item.service_type == service_type
        and (not specialty or item.specialty_name.casefold() == specialty.casefold())
    ]
    if "available" in statuses:
        return "available"
    if "unavailable" in statuses:
        return "unavailable"
    return "unknown"


def serialize_hospital(hospital, origin=None):
    coordinates = _valid_coordinates(hospital.latitude, hospital.longitude)
    distance = None
    if origin and coordinates:
        distance = round(haversine_km(*origin, *coordinates), 1)
    services = list(hospital.services.all())
    sources = _provider_sources(hospital)
    verification_status = _provider_trust_status(hospital, sources)
    contact_rows = list(getattr(hospital, "_provider_contacts", [])) or list(hospital.provider_contacts.all())
    phone_contact = next((item for item in contact_rows if item.contact_type == "phone" and item.value == hospital.phone), None)
    phone_contact_status = phone_contact.verification_status if phone_contact else "unverified"
    safe_phone = _safe_phone(hospital.phone)
    phone_visible = bool(safe_phone and hospital.effective_verification_status in {"confirmed", "verified"} and phone_contact_status not in {"rejected", "revoked", "pending"})
    return {
        "id": hospital.pk,
        "name": hospital.name,
        "facility_type": hospital.facility_type,
        "city": hospital.city,
        "address": hospital.address,
        "latitude": coordinates[0] if coordinates else None,
        "longitude": coordinates[1] if coordinates else None,
        "phone": safe_phone if phone_visible else None,
        "phone_contact_status": phone_contact_status if phone_visible else None,
        "phone_contact_label": ("Verified contact" if phone_contact_status == "verified" else "Unverified contact information") if phone_visible else None,
        "website": _safe_source_url(hospital.website),
        "is_demo": hospital.is_demo,
        "verification_status": verification_status,
        "trust_label": _trust_label(verification_status, hospital),
        "sources": sources,
        "contacts": _provider_contacts(hospital, verification_status),
        "updated_at": hospital.updated_at.isoformat(),
        "distance_km": distance,
        "services": [
            {
                "type": service.service_type,
                "name": service.specialty_name or service.get_service_type_display(),
                "status": service.effective_status,
                "is_demo": hospital.is_demo,
                "status_label": (
                    f"Demo status: {service.effective_status}"
                    if hospital.is_demo else f"Reported {service.effective_status}"
                ),
                "source": service.source,
                "updated_at": service.updated_at.isoformat(),
                "expires_at": service.expires_at.isoformat() if service.expires_at else None,
            }
            for service in services
        ],
    }


def search_hospitals(query="", location="", latitude=None, longitude=None, emergency=False, icu=False, trauma=False, specialty=""):
    """Search actual ORM records; distance origin is user-provided coordinates."""
    query = (query or "").strip()
    location = (location or "").strip()
    specialty = (specialty or "").strip()
    origin = _valid_coordinates(latitude, longitude)
    if origin is None:
        origin = resolve_manual_location(location)

    hospitals = Hospital.objects.prefetch_related(
        "services", "doctors", "doctor_affiliations__doctor__specialty_links__specialty",
        "source_records", Prefetch("verification_records", queryset=ProviderVerification.objects.order_by("-created_at", "-pk"), to_attr="_provider_verifications"),
        "provider_contacts",
    ).all()
    if query:
        hospitals = hospitals.filter(
            Q(name__icontains=query) | Q(city__icontains=query) | Q(address__icontains=query)
        )
    # Each supplied area token must match the stored city or address text.
    for location_part in (part.strip() for part in location.split(",") if part.strip()):
        hospitals = hospitals.filter(Q(city__icontains=location_part) | Q(address__icontains=location_part))

    results = []
    for hospital in hospitals.distinct():
        if emergency and _service_status(hospital, "emergency") != "available":
            continue
        if icu and _service_status(hospital, "icu") != "available":
            continue
        if trauma and _service_status(hospital, "trauma") != "available":
            continue
        if specialty:
            has_service = _service_status(hospital, "specialty", specialty) == "available"
            affiliated = Doctor.objects.filter(
                Q(affiliations__hospital=hospital, affiliations__is_current=True)
                | Q(hospital=hospital, affiliations__isnull=True)
            ).distinct().prefetch_related("specialty_links__specialty")
            has_doctor = any(
                specialty.casefold() in doctor.specialization.casefold()
                or any(specialty.casefold() in link.specialty.name.casefold() for link in doctor.specialty_links.all() if link.specialty.is_active)
                for doctor in affiliated
            )
            if not (has_service or has_doctor):
                continue
        results.append(serialize_hospital(hospital, origin))

    if origin:
        results.sort(key=lambda item: item["distance_km"] if item["distance_km"] is not None else float("inf"))
    return results


def search_mapped_facilities(latitude, longitude, radius_km=5):
    """Discover transient OSM results without mixing them into managed records."""
    return discover_facilities(latitude, longitude, radius_km)


def _managed_discovery_result(item, result_type, origin=None):
    result = dict(item)
    identifier = item["id"]
    canonical_type = "hospital" if result_type == "facility" else result_type
    result.update({
        "result_id": f"managed:{canonical_type}:{identifier}",
        "result_type": canonical_type,
        "source": "MediReach",
        "source_category": "managed_record",
        "trust_category": item.get("provider_status", item.get("verification_status", "unverified")),
        "source_types": list(dict.fromkeys(source.get("source_type") for source in item.get("sources", []) if source.get("source_type"))),
    })
    if result_type == "doctor":
        city = item.get("city")
        facilities = item.get("facilities", [])
        location_values = [city] if city else []
        for facility in facilities:
            location_values.extend(value for value in (facility.get("city"), facility.get("address")) if value)
        result["location"] = {"affiliations": "; ".join(dict.fromkeys(location_values))} if location_values else {}
        facility_points = [
            (facility, _valid_coordinates(facility.get("latitude"), facility.get("longitude")))
            for facility in facilities
        ]
        facility_points = [(facility, point) for facility, point in facility_points if point]
        if origin and facility_points:
            facility_points.sort(key=lambda pair: haversine_km(*origin, *pair[1]))
        coordinates = facility_points[0][1] if facility_points else None
        if coordinates:
            result["coordinates"] = {"latitude": coordinates[0], "longitude": coordinates[1]}
            if origin:
                result["distance_km"] = round(haversine_km(*origin, *coordinates), 1)
    else:
        city = item.get("city")
        address = item.get("address")
        result["location"] = {key: value for key, value in {"city": city, "address": address}.items() if value}
        if item.get("latitude") is not None and item.get("longitude") is not None:
            result["coordinates"] = {"latitude": item["latitude"], "longitude": item["longitude"]}
        if item.get("distance_km") is None and origin and result.get("coordinates"):
            result["distance_km"] = round(haversine_km(origin[0], origin[1], item["latitude"], item["longitude"]), 1)
    result["contact_information"] = list(item.get("contacts", []))
    safe_phone = _safe_phone(item.get("phone"))
    if safe_phone and not any(contact.get("value") == safe_phone for contact in result["contact_information"]):
        result["contact_information"].append({
            "type": "phone", "value": safe_phone,
            "verification_status": item.get("phone_contact_status", "unverified"),
            "label": item.get("phone_contact_label", "Unverified contact information"),
        })
    if item.get("website") and not any(contact.get("value") == item["website"] for contact in result["contact_information"]):
        result["contact_information"].append({
            "type": "website", "value": item["website"],
            "verification_status": "unverified", "label": "Unverified stored website",
        })
    return result


def _osm_discovery_result(item, origin=None):
    result = dict(item)
    result.update({
        "result_id": f"osm:{item['osm_type']}:{item['osm_id']}",
        "result_type": "osm_facility",
        "source": "OpenStreetMap",
        "source_category": "openstreetmap",
        "trust_category": "mapped_unverified",
        "location": dict(item.get("address", {})),
        "coordinates": {"latitude": item["latitude"], "longitude": item["longitude"]},
        "contact_information": [
            {"type": key, "value": _safe_phone(item[key]) if key == "phone" else item[key], "verification_status": "unverified", "label": "OpenStreetMap mapped contact; not independently verified"}
            for key in ("phone", "website") if item.get(key) and (key != "phone" or _safe_phone(item[key]))
        ],
    })
    if origin:
        result["distance_km"] = round(haversine_km(*origin, item["latitude"], item["longitude"]), 1)
    return result


def _discovery_error(source, exc):
    return {
        "source": source,
        "message": str(exc),
        "reason": getattr(exc, "reason", "unavailable"),
        "status_code": getattr(exc, "status_code", None),
        "retry_after": getattr(exc, "retry_after", None),
    }


def _filter_discovery_result(result, *, query="", facility_type="", specialty="", location="", trust_category="", source_category=""):
    query = query.casefold().strip()
    facility_type = facility_type.casefold().strip()
    specialty = specialty.casefold().strip()
    location = location.casefold().strip()
    trust_category = trust_category.casefold().strip()
    source_category = source_category.casefold().strip()
    if query:
        search_values = [
            result.get(key, "")
            for key in ("name", "city", "address", "facility_category", "facility_type", "specialty")
        ]
        search_values.extend(result.get("specialties") or [])
        search_values.extend(
            service.get("name", "")
            for service in result.get("services", [])
            if isinstance(service, dict)
        )
        if query not in " ".join(str(value) for value in search_values).casefold():
            return False
    category = str(result.get("facility_type") or result.get("facility_category") or "").casefold()
    facility_aliases = {
        "diagnostic_centre": {"diagnostic_centre", "diagnostic_center", "laboratory"},
        "imaging_centre": {"imaging_centre", "imaging_center", "imaging", "radiology"},
        "clinic": {"clinic", "medical_centre", "medical_center"},
    }
    if facility_type and category not in facility_aliases.get(facility_type, {facility_type}):
        return False
    if specialty:
        labels = result.get("specialties") or ([result.get("specialty")] if result.get("specialty") else [])
        services = result.get("services", [])
        terms = specialty_terms(specialty)
        category_match = any(term in specialty_terms(result.get("facility_category", "")) for term in terms)
        if not category_match and not any(term in str(label).casefold() for label in labels for term in terms) and not any(
            term in str(service.get("name", "")).casefold() for service in services for term in terms
        ):
            return False
    if location:
        location_text = " ".join(str(value) for value in result.get("location", {}).values()).casefold()
        if location not in location_text and location not in str(result.get("city", "")).casefold():
            return False
    if trust_category and result.get("trust_category", "").casefold() != trust_category:
        return False
    if source_category:
        categories = {result.get("source_category", "").casefold(), *(value.casefold() for value in result.get("source_types", []))}
        if source_category not in categories:
            return False
    return True


def discover_providers(
    *, result_types=("doctor", "hospital"), query="", facility_type="", specialty="",
    location="", latitude=None, longitude=None, radius_km=5, include_osm=False,
    trust_category="", source_category="", emergency=False, icu=False, trauma=False,
    source_errors=None,
):
    """Unified read boundary; managed and OSM records remain separate results."""
    aliases = {"doctors": "doctor", "hospitals": "hospital", "facilities": "hospital", "facility": "hospital"}
    if isinstance(result_types, str):
        result_types = (result_types,)
    selected_types = {aliases.get(value, value) for value in result_types}
    unsupported = selected_types - {"doctor", "hospital"}
    if unsupported:
        raise ValueError("Unsupported provider result type.")
    origin = _valid_coordinates(latitude, longitude)
    explicit_origin = origin is not None
    if (latitude is None) != (longitude is None) or ((latitude is not None or longitude is not None) and origin is None):
        raise ValueError("Provide valid latitude and longitude together.")
    if isinstance(radius_km, bool):
        raise ValueError("Radius must be a number between zero and 20 km.")
    try:
        radius_km = float(radius_km)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Radius must be a number between zero and 20 km.")
    if not isfinite(radius_km) or not 0 < radius_km <= MAX_RADIUS_KM:
        raise ValueError(f"Radius must be greater than zero and no more than {MAX_RADIUS_KM} km.")
    if include_osm and origin is None:
        if location:
            try:
                origin = resolve_manual_location(location)
                if origin is None:
                    resolved = resolve_location(location)
                    origin = (resolved["latitude"], resolved["longitude"])
                latitude, longitude = origin
            except LocationResolutionError as exc:
                if source_errors is None:
                    raise
                source_errors.append(_discovery_error("Location", exc))
                include_osm = False
        if include_osm and origin is None:
            raise ValueError("Coordinates or a resolvable area are required for OpenStreetMap discovery.")

    results = []
    mapped_records = None
    mapped_attempted = False

    def get_mapped_records():
        nonlocal mapped_records, mapped_attempted
        if mapped_attempted:
            return mapped_records
        mapped_attempted = True
        try:
            mapped_records = search_mapped_facilities(latitude, longitude, radius_km)
        except FacilityDiscoveryError as exc:
            if source_errors is None:
                raise
            source_errors.append(_discovery_error("OpenStreetMap", exc))
            mapped_records = []
        return mapped_records

    if "doctor" in selected_types:
        for item in search_doctors(query=query, specialty=specialty, location=location):
            result = _managed_discovery_result(item, "doctor", origin)
            if explicit_origin and radius_km is not None and (result.get("distance_km") is None or result["distance_km"] > float(radius_km)):
                continue
            if _filter_discovery_result(result, query=query, specialty=specialty, location=location, trust_category=trust_category, source_category=source_category):
                results.append(result)
        if include_osm:
            for item in get_mapped_records():
                result = _osm_discovery_result(item, origin)
                # OSM points are facility listings, never individual clinician profiles.
                if result.get("facility_category") not in {"doctor", "dentist"}:
                    continue
                if _filter_discovery_result(result, query=query, specialty=specialty, trust_category=trust_category, source_category=source_category):
                    results.append(result)
    if "hospital" in selected_types:
        for item in search_hospitals(
            query=query, location=location, latitude=latitude, longitude=longitude,
            specialty=specialty, emergency=emergency, icu=icu, trauma=trauma,
        ):
            result = _managed_discovery_result(item, "facility", origin)
            if facility_type and str(item.get("facility_type") or "").casefold() != facility_type.casefold():
                continue
            if explicit_origin and radius_km is not None and (result.get("distance_km") is None or result["distance_km"] > float(radius_km)):
                continue
            # search_hospitals already checks services and current affiliated doctor specialties.
            if _filter_discovery_result(result, query=query, facility_type=facility_type, specialty="", location=location, trust_category=trust_category, source_category=source_category):
                results.append(result)
    if include_osm and "hospital" in selected_types:
        for item in get_mapped_records():
            result = _osm_discovery_result(item, origin)
            if _filter_discovery_result(result, query=query, facility_type=facility_type, specialty=specialty, trust_category=trust_category, source_category=source_category):
                results.append(result)
    # Stable managed IDs and exact OSM type/ID are the only deduplication keys.
    unique_results = {}
    for result in results:
        unique_results.setdefault(result["result_id"], result)
    results = list(unique_results.values())
    results.sort(key=lambda item: (
        item.get("distance_km") is None,
        item.get("distance_km") if item.get("distance_km") is not None else float("inf"),
        item["result_id"],
    ))
    return results


def get_hospital_details(hospital_id):
    hospital = Hospital.objects.prefetch_related(
        "services", "doctors", "source_records",
        Prefetch("verification_records", queryset=ProviderVerification.objects.order_by("-created_at", "-pk"), to_attr="_provider_verifications"),
        "provider_contacts",
    ).filter(pk=hospital_id).first()
    return serialize_hospital(hospital) if hospital else None


def doctors_for_hospital(hospital):
    """Return current affiliations, using the legacy FK only before affiliations exist."""
    return doctor_queryset().filter(
        Q(affiliations__hospital=hospital, affiliations__is_current=True)
        | Q(hospital=hospital, affiliations__isnull=True)
    ).distinct()


def search_doctors(specialty="", location="", query=""):
    doctors = doctor_queryset(query=query, specialty=specialty, location=location)
    return [serialize_doctor(doctor) for doctor in doctors]


def _provider_sources(provider):
    sources = getattr(provider, "_provider_sources", None)
    if sources is None:
        sources = provider.source_records.all()
    return [
        {
            "source_type": item.source_type,
            "source_name": item.source_name,
            "source_url": _safe_source_url(item.source_url),
            "source_updated_at": item.source_updated_at.isoformat() if item.source_updated_at else None,
            "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
        }
        for item in sources
    ]


def _safe_source_url(value):
    """Expose provenance links only when they use an explicit web scheme."""
    if not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.username and not parsed.password else None


def _safe_contact_route(value):
    """Allow only same-site paths or credential-free HTTP(S) contact links."""
    if not value:
        return None
    candidate = str(value).strip()
    if not candidate or any(ord(character) < 32 for character in candidate) or "\\" in candidate:
        return None
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme:
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
            return candidate
        return None
    if parsed.netloc or not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return None
    return candidate


def _provider_trust_status(provider, sources=None):
    if getattr(provider, "is_demo", False) or getattr(provider, "verification_status", None) == "demo":
        return "demo"
    sources = sources if sources is not None else _provider_sources(provider)
    if any(source["source_type"] == "demo_data" for source in sources):
        return "demo"
    records = getattr(provider, "_provider_verifications", None)
    if records is None:
        records = provider.verification_records.order_by("-created_at", "-pk")
    latest = next(iter(records), None)
    if latest is None:
        return "unverified"
    if latest.status == "verified" and latest.expires_at and latest.expires_at <= timezone.now():
        return "expired"
    return latest.status


def _trust_label(status, provider=None):
    demo_label = "DEMO — fictional facility; not verified" if isinstance(provider, Hospital) else "DEMO — fictional profile; DEMO profile is not verified"
    return {
        "demo": demo_label,
        "unverified": "Unverified — no current verification record",
        "pending": "Verification pending",
        "verified": "Verified",
        "rejected": "Verification rejected",
        "revoked": "Verification revoked",
        "expired": "Verification expired",
    }.get(status, "Unverified")


def _provider_contacts(provider, provider_status):
    if provider_status == "demo":
        return []
    contacts = getattr(provider, "_provider_contacts", None)
    if contacts is None:
        contacts = provider.provider_contacts.all()
    result = []
    for contact in contacts:
        if contact.verification_status in {"rejected", "revoked", "pending"}:
            continue
        if contact.contact_type == "phone" and not _safe_phone(contact.value):
            continue
        if contact.contact_type == "website" and not _safe_source_url(contact.value):
            continue
        if isinstance(provider, Hospital) and provider.effective_verification_status not in {"confirmed", "verified"}:
            continue
        if contact.verification_status == "verified":
            value = _safe_source_url(contact.value) if contact.contact_type == "website" else contact.value
            result.append({"type": contact.contact_type, "value": value, "verification_status": "verified", "label": "Verified contact"})
            continue
        # A new unverified contact cannot widen existing contact visibility.
        if isinstance(provider, Hospital) and contact.contact_type in {"phone", "website"}:
            value = _safe_source_url(contact.value) if contact.contact_type == "website" else contact.value
            result.append({"type": contact.contact_type, "value": value, "verification_status": "unverified", "label": "Unverified contact information"})
    return result


def _doctor_specialty_labels(doctor):
    links = getattr(doctor, "_structured_specialties", None)
    if links is None:
        links = doctor.specialty_links.select_related("specialty").filter(specialty__is_active=True)
    labels = [link.specialty.name for link in links if link.specialty.is_active]
    if doctor.specialization:
        labels.append(doctor.specialization)
    unique = {}
    for label in labels:
        if label and label.strip():
            unique.setdefault(label.strip().casefold(), label.strip())
    return list(unique.values())


def _doctor_facility_records(doctor):
    affiliations = getattr(doctor, "_provider_affiliations", None)
    if affiliations is None:
        affiliations = list(doctor.affiliations.filter(is_current=True).select_related("hospital"))
    current = [item for item in affiliations if item.is_current]
    if current:
        selected = sorted(current, key=lambda item: (not item.is_primary, item.hospital.name.casefold(), item.hospital_id))
        return [(item.hospital, item.is_primary) for item in selected]
    # A legacy FK is a current fallback only when no affiliation history exists.
    if not affiliations and doctor.hospital_id:
        return [(doctor.hospital, True)]
    return []


def serialize_doctor(doctor):
    sources = _provider_sources(doctor)
    status = _provider_trust_status(doctor, sources)
    labels = _doctor_specialty_labels(doctor)
    facilities = []
    seen = set()
    for hospital, primary in _doctor_facility_records(doctor):
        if hospital.pk in seen:
            continue
        seen.add(hospital.pk)
        coordinates = _valid_coordinates(hospital.latitude, hospital.longitude)
        facility_data = serialize_hospital(hospital)
        facilities.append({
            "id": hospital.pk, "name": hospital.name, "city": hospital.city,
            "address": facility_data["address"], "phone": facility_data["phone"],
            "phone_contact_label": facility_data["phone_contact_label"],
            "website": facility_data["website"],
            "latitude": coordinates[0] if coordinates else None,
            "longitude": coordinates[1] if coordinates else None,
            "is_demo": hospital.is_demo,
            "verification_status": hospital.effective_verification_status,
            "is_primary": primary,
        })
    primary = next((item for item in facilities if item["is_primary"]), facilities[0] if facilities else None)
    legacy_status = "demo" if status == "demo" else (status if status in {"confirmed", "verified", "unknown", "expired"} else "unknown")
    contacts = _provider_contacts(doctor, status)
    verifications = list(getattr(doctor, "_provider_verifications", []))
    qualification_verified = status == "verified" and any(
        record.verification_type == "qualification" and record.status == "verified"
        and record.evidence_reference and record.verified_by_id and record.verified_at
        and (not record.expires_at or record.expires_at > timezone.now())
        for record in verifications
    )
    return {
        "id": doctor.pk,
        "name": doctor.name,
        "qualification": doctor.qualification if qualification_verified else None,
        "qualification_label": "Verified qualification" if qualification_verified else "Qualification details not available from a verified source",
        "experience": None,
        "specialty": ", ".join(labels),
        "specialties": labels,
        "hospital": primary["name"] if primary else None,
        "city": primary["city"] if primary else None,
        "facilities": facilities,
        "contact_route": _safe_contact_route(doctor.contact_route),
        "contacts": contacts,
        "sources": sources,
        "verification_status": legacy_status,
        "provider_status": status,
        "trust_label": _trust_label(status, doctor),
        "registration_number": doctor.registration_number if (
            status == "verified" and doctor.registration_number and any(
                record.verification_type == "registration" and record.status == "verified"
                and record.evidence_reference and record.verified_by_id and record.verified_at
                and (not record.expires_at or record.expires_at > timezone.now())
                for record in getattr(doctor, "_provider_verifications", [])
            )
        ) else None,
    }


def doctor_queryset(query="", specialty="", location=""):
    """Return doctor records matching every supplied filter."""
    query = (query or "").strip()
    specialty = (specialty or "").strip()
    location = (location or "").strip()
    doctors = Doctor.objects.select_related("hospital").prefetch_related(
        Prefetch("affiliations", queryset=DoctorHospitalAffiliation.objects.select_related("hospital").order_by("-is_current", "-is_primary", "hospital__name", "pk"), to_attr="_provider_affiliations"),
        Prefetch("specialty_links", queryset=DoctorSpecialty.objects.select_related("specialty").filter(specialty__is_active=True), to_attr="_structured_specialties"),
        Prefetch("source_records", queryset=ProviderSourceRecord.objects.only("doctor_id", "hospital_id", "source_type", "source_name", "source_url", "source_updated_at", "retrieved_at"), to_attr="_provider_sources"),
        Prefetch("verification_records", queryset=ProviderVerification.objects.order_by("-created_at", "-pk"), to_attr="_provider_verifications"),
        Prefetch("provider_contacts", queryset=ProviderContact.objects.order_by("contact_type", "-is_primary", "pk"), to_attr="_provider_contacts"),
    ).all()
    if specialty:
        specialty_query = Q()
        for term in specialty_terms(specialty):
            specialty_query |= (
                Q(specialization__icontains=term)
                | Q(specialty_links__specialty__is_active=True, specialty_links__specialty__name__icontains=term)
                | Q(specialty_links__specialty__is_active=True, specialty_links__specialty__slug__icontains=term)
            )
        doctors = doctors.filter(specialty_query)
    if location:
        for location_part in (part.strip() for part in location.split(",") if part.strip()):
            doctors = doctors.filter(
                Q(affiliations__is_current=True, affiliations__hospital__city__icontains=location_part)
                | Q(affiliations__is_current=True, affiliations__hospital__address__icontains=location_part)
                | Q(affiliations__isnull=True, hospital__city__icontains=location_part)
                | Q(affiliations__isnull=True, hospital__address__icontains=location_part)
            )
    if query:
        doctors = doctors.filter(
            Q(name__icontains=query) | Q(specialization__icontains=query)
            | Q(specialty_links__specialty__is_active=True, specialty_links__specialty__name__icontains=query)
        )
    return doctors.order_by("name", "pk").distinct()


def retrieve_first_aid_guide(category=None):
    if category:
        return get_first_aid_guide(category)
    return list_first_aid_guides()


def get_emergency_contacts(user=None):
    contacts = []
    if user and user.is_authenticated:
        contacts = list(user.emergency_contacts.values("id", "name", "phone", "relationship"))
    return {"public_emergency_number": "112", "contacts": contacts}


def generate_emergency_summary(reported_facts, location_consent=False, latitude=None, longitude=None):
    """Format user-reported facts without diagnosis or inferred findings."""
    keys = {
        "symptoms": "Symptoms reported",
        "onset": "Onset/duration reported",
        "temperature": "Temperature reported",
        "relevant_information": "Relevant information reported",
        "actions_taken": "Actions already taken",
    }
    summary = {
        "title": "Emergency handover summary",
        "reported_facts": {
            label: str(reported_facts.get(key, "")).strip()
            for key, label in keys.items()
            if str(reported_facts.get(key, "")).strip()
        },
        "inferred_information": [],
        "location_shared": False,
        "emergency_number": "112",
        "generated_at": timezone.now().isoformat(),
        "notice": "This summary contains only information entered by the user. It is not a diagnosis and has not been sent to emergency services.",
    }
    if location_consent and latitude is not None and longitude is not None:
        try:
            lat, lon = float(latitude), float(longitude)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                summary["location_shared"] = True
                summary["reported_facts"]["Location shared by user"] = f"{lat:.5f}, {lon:.5f}"
        except (TypeError, ValueError):
            pass
    return summary
