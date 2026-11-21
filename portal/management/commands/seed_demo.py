from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from portal.models import Doctor, AppointmentSlot, Hospital, HospitalService

class Command(BaseCommand):
    help = "Create fictional doctors and future appointment slots for a demo."
    def handle(self, *args, **options):
        facilities = [
            ("MediReach Demo Emergency Centre - Pune", "Pune", "DEMONSTRATION LOCATION ONLY; not a real facility or address.", 18.5204, 73.8567),
            ("MediReach Demo Care Centre - Mumbai", "Mumbai", "DEMONSTRATION LOCATION ONLY; not a real facility or address.", 19.0760, 72.8777),
            ("MediReach Demo Medical Centre - Delhi", "Delhi", "DEMONSTRATION LOCATION ONLY; not a real facility or address.", 28.6139, 77.2090),
            ("MediReach Demo Health Centre - Bengaluru", "Bengaluru", "DEMONSTRATION LOCATION ONLY; not a real facility or address.", 12.9716, 77.5946),
        ]
        demo_hospitals = {}
        for name, city, address, lat, lon in facilities:
            hospital, _ = Hospital.objects.update_or_create(name=name, defaults={
                "city": city, "address": address, "latitude": lat, "longitude": lon,
                "phone": "", "website": "", "is_demo": True, "verification_status": "demo",
            })
            demo_hospitals[city] = hospital
            for kind in ("emergency", "icu", "trauma"):
                HospitalService.objects.update_or_create(hospital=hospital, service_type=kind, specialty_name="", defaults={
                    "status": "available" if (city, kind) in {( "Pune", "emergency"), ("Mumbai", "emergency"), ("Delhi", "icu"), ("Bengaluru", "trauma")} else "unknown",
                    "source": "Demonstration data only; not confirmed by a facility",
                    "details": "Example directory status only. Not live capacity information.",
                    "expires_at": timezone.now() + timedelta(days=30),
                })
        samples = [
            ("Dr. Mira Shah", "Family Medicine", 12, "MBBS, MD", "A primary care clinician focused on preventive health."),
            ("Dr. Arjun Mehta", "Cardiology", 15, "MBBS, DM Cardiology", "A fictional cardiology profile for project demonstration."),
            ("Dr. Neha Rao", "Dermatology", 9, "MBBS, MD Dermatology", "A fictional dermatology profile for project demonstration."),
            ("Dr. Kabir Sen", "Pediatrics", 11, "MBBS, DCH", "A fictional pediatric profile for project demonstration."),
        ]
        created = 0
        for name, specialty, experience, qualification, bio in samples:
            city = {"Cardiology": "Mumbai", "Dermatology": "Delhi", "Pediatrics": "Bengaluru"}.get(specialty, "Pune")
            doctor, _ = Doctor.objects.get_or_create(name=name, defaults={"specialization": specialty, "experience": experience, "qualification": qualification, "bio": bio, "fee": 500, "hospital": demo_hospitals[city], "contact_route": f"/hospitals/{demo_hospitals[city].pk}/", "verification_status": "demo"})
            for day in range(1, 15):
                date = (timezone.localdate() + timedelta(days=day))
                for hour in (10, 14, 16):
                    starts = timezone.make_aware(timezone.datetime.combine(date, time(hour, 0)))
                    _, was_created = AppointmentSlot.objects.get_or_create(doctor=doctor, starts_at=starts)
                    created += was_created
        self.stdout.write(self.style.SUCCESS(f"Demo seed complete: {len(samples)} fictional doctors; {created} new slots."))
