from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from portal.models import Doctor, AppointmentSlot

class Command(BaseCommand):
    help = "Create fictional doctors and future appointment slots for a demo."
    def handle(self, *args, **options):
        samples = [
            ("Dr. Mira Shah", "Family Medicine", 12, "MBBS, MD", "A primary care clinician focused on preventive health."),
            ("Dr. Arjun Mehta", "Cardiology", 15, "MBBS, DM Cardiology", "A fictional cardiology profile for project demonstration."),
            ("Dr. Neha Rao", "Dermatology", 9, "MBBS, MD Dermatology", "A fictional dermatology profile for project demonstration."),
            ("Dr. Kabir Sen", "Pediatrics", 11, "MBBS, DCH", "A fictional pediatric profile for project demonstration."),
        ]
        created = 0
        for name, specialty, experience, qualification, bio in samples:
            doctor, _ = Doctor.objects.get_or_create(name=name, defaults={"specialization": specialty, "experience": experience, "qualification": qualification, "bio": bio, "fee": 500})
            for day in range(1, 15):
                date = (timezone.localdate() + timedelta(days=day))
                for hour in (10, 14, 16):
                    starts = timezone.make_aware(timezone.datetime.combine(date, time(hour, 0)))
                    _, was_created = AppointmentSlot.objects.get_or_create(doctor=doctor, starts_at=starts)
                    created += was_created
        self.stdout.write(self.style.SUCCESS(f"Demo seed complete: {len(samples)} fictional doctors; {created} new slots."))
