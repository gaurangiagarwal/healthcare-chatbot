from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent


class FrontendIntegrationRegressionTests(SimpleTestCase):
    def read(self, relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_shared_navigation_has_active_routes_and_accessible_mobile_controls(self):
        template = self.read("templates/portal/base.html")
        script = self.read("static/portal/navigation.js")
        self.assertIn("request.resolver_match.url_name == 'doctor_detail'", template)
        self.assertIn("request.resolver_match.url_name == 'hospital_detail'", template)
        self.assertIn("request.resolver_match.url_name == 'referral_new'", template)
        self.assertIn('aria-controls="app-sidebar" aria-expanded="false"', template)
        self.assertIn('id="sidebar-backdrop"', template)
        self.assertIn("event.key === 'Escape'", script)
        self.assertIn("toggleAttribute('inert'", script)
        self.assertIn("form[method=\"post\"]", script)

    def test_provider_journey_links_keep_trust_and_source_prominent(self):
        doctors = self.read("templates/portal/doctors.html")
        doctor_detail = self.read("templates/portal/doctor_detail.html")
        hospitals = self.read("templates/portal/hospitals.html")
        chat = self.read("static/portal/chatbot.js")
        self.assertIn("doctor.trust_label", doctors)
        self.assertIn("provider.trust_label", doctor_detail)
        self.assertIn("hospital.trust_label", hospitals)
        self.assertIn("View doctor profile and local slots", chat)
        self.assertIn("facility.source_url?.startsWith('https://')", self.read("static/portal/hospital-finder.js"))

    def test_chat_and_map_keep_safe_rendering_and_clear_failure_fallbacks(self):
        chat = self.read("static/portal/chatbot.js")
        finder = self.read("static/portal/hospital-finder.js")
        hospitals = self.read("templates/portal/hospitals.html")
        self.assertIn("bubble.textContent = text", chat)
        self.assertIn("link('Call 112 now', 'tel:112'", chat)
        self.assertIn("The map library did not load.", finder)
        self.assertIn("Map tiles were blocked or could not be loaded.", finder)
        self.assertIn("referrerPolicy: 'strict-origin-when-cross-origin'", finder)
        self.assertIn("directoryForm.requestSubmit()", finder)
        self.assertIn("id=\"map-tile-status\"", hospitals)
        self.assertIn("Search and map diagnostics", hospitals)
        self.assertIn("The directory list remains available if the map does not load", hospitals)
        self.assertIn("aria-live=\"polite\"", hospitals)

    def test_responsive_and_trust_styles_cover_small_screens(self):
        css = self.read("static/portal/style.css")
        self.assertIn("@media(max-width:1100px)", css)
        self.assertIn("@media(max-width:700px)", css)
        self.assertIn("@media(max-width:390px)", css)
        for status in ("demo", "verified", "pending", "unverified", "rejected", "revoked", "expired", "mapped"):
            self.assertIn(f"trust-status.{status}", css)
