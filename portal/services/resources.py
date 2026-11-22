"""Backend tools for curated aid, demo resource discovery and handovers."""
from math import asin, cos, radians, sin, sqrt

from django.utils import timezone

from portal.models import Doctor, EmergencyContact, Hospital, HospitalService
from portal.services.first_aid import get_first_aid_guide, list_first_aid_guides


CITY_CENTRES = {
    "pune": (18.5204, 73.8567),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km, using a spherical Earth approximation."""
    lat1, lon1, lat2, lon2 = map(radians, (float(lat1), float(lon1), float(lat2), float(lon2)))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def resolve_manual_location(location):
    text = (location or "").strip().lower()
    if not text:
        return None
    if "," in text:
        try:
            lat, lon = (float(part.strip()) for part in text.split(",", 1))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass
    for city, coordinates in CITY_CENTRES.items():
        if city in text:
            return coordinates
    return None


def _service_status(hospital, service_type, specialty=""):
    service = next(
        (
            item for item in hospital.services.all()
            if item.service_type == service_type
            and (not specialty or item.specialty_name.casefold() == specialty.casefold())
        ),
        None,
    )
    return service.effective_status if service else "unknown"


def serialize_hospital(hospital, origin=None):
    distance = None
    if origin and hospital.latitude is not None and hospital.longitude is not None:
        distance = round(haversine_km(*origin, hospital.latitude, hospital.longitude), 1)
    services = list(hospital.services.all())
    return {
        "id": hospital.pk,
        "name": hospital.name,
        "city": hospital.city,
        "address": hospital.address,
        "latitude": float(hospital.latitude) if hospital.latitude is not None else None,
        "longitude": float(hospital.longitude) if hospital.longitude is not None else None,
        "phone": hospital.phone if hospital.phone and hospital.effective_verification_status in {"confirmed", "verified"} else None,
        "website": hospital.website or None,
        "is_demo": hospital.is_demo,
        "verification_status": hospital.effective_verification_status,
        "updated_at": hospital.updated_at.isoformat(),
        "distance_km": distance,
        "services": [
            {
                "type": service.service_type,
                "name": service.specialty_name or service.get_service_type_display(),
                "status": service.effective_status,
                "source": service.source,
                "updated_at": service.updated_at.isoformat(),
                "expires_at": service.expires_at.isoformat() if service.expires_at else None,
            }
            for service in services
        ],
    }


def search_hospitals(query="", location="", latitude=None, longitude=None, emergency=False, icu=False, trauma=False, specialty=""):
    """Search actual ORM records; distance origin is user-provided coordinates."""
    origin = None
    try:
        if latitude is not None and longitude is not None:
            lat, lon = float(latitude), float(longitude)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                origin = (lat, lon)
    except (TypeError, ValueError):
        origin = None
    if origin is None:
        origin = resolve_manual_location(location)

    hospitals = Hospital.objects.prefetch_related("services", "doctors").all()
    if query:
        hospitals = hospitals.filter(name__icontains=query) | hospitals.filter(city__icontains=query) | hospitals.filter(address__icontains=query)
    # City names restrict the result set; typed coordinates only establish a
    # distance origin and should not be mistaken for a city filter.
    if location and "," not in location:
        hospitals = hospitals.filter(city__icontains=location) | hospitals.filter(address__icontains=location)

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
            has_doctor = any(specialty.casefold() in doctor.specialization.casefold() for doctor in hospital.doctors.all())
            if not (has_service or has_doctor):
                continue
        results.append(serialize_hospital(hospital, origin))

    if origin:
        results.sort(key=lambda item: item["distance_km"] if item["distance_km"] is not None else float("inf"))
    return results


def get_hospital_details(hospital_id):
    hospital = Hospital.objects.prefetch_related("services", "doctors").filter(pk=hospital_id).first()
    return serialize_hospital(hospital) if hospital else None


def search_doctors(specialty="", location="", query=""):
    doctors = Doctor.objects.select_related("hospital").all()
    if specialty:
        doctors = doctors.filter(specialization__icontains=specialty)
    if location:
        doctors = doctors.filter(hospital__city__icontains=location)
    if query:
        doctors = doctors.filter(name__icontains=query) | doctors.filter(specialization__icontains=query)
    return [
        {
            "id": doctor.pk,
            "name": doctor.name,
            "specialty": doctor.specialization,
            "hospital": doctor.hospital.name if doctor.hospital_id else None,
            "city": doctor.hospital.city if doctor.hospital_id else None,
            "contact_route": doctor.contact_route or None,
            "verification_status": doctor.verification_status,
        }
        for doctor in doctors.distinct()
    ]


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
