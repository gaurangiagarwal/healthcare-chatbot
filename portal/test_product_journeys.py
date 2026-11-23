import json
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase, override_settings

from portal.services.chat import respond
from portal.services.locations import LocationResolutionError, normalize_location, resolve_location


class LocationResolutionTests(SimpleTestCase):
    def setUp(self):
        from portal.services import locations
        locations._cache.clear()
        locations._error_cache.clear()

    def test_location_input_normalizes_areas_and_validates_indian_pin_codes(self):
        self.assertEqual(normalize_location("  Sector 62,   Noida  "), "Sector 62, Noida")
        self.assertEqual(normalize_location("201301"), "201301")
        with self.assertRaises(ValueError):
            normalize_location("012345")
        with self.assertRaises(ValueError):
            normalize_location("x" * 121)

    @override_settings(RUNNING_TESTS=False)
    @patch("portal.services.locations.urlopen")
    @patch("portal.services.locations._throttle_request")
    def test_user_triggered_lookup_returns_valid_coordinates_and_is_cached(self, throttle, urlopen):
        payload = [{"lat": "28.6139", "lon": "77.2090", "display_name": "New Delhi, India"}]
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(payload).encode()
        urlopen.return_value = response

        first = resolve_location("Delhi-test-cache")
        second = resolve_location("  delhi-test-cache ")

        self.assertEqual(first["latitude"], 28.6139)
        self.assertEqual(first["longitude"], 77.209)
        self.assertEqual(second, first)
        urlopen.assert_called_once()

    @override_settings(RUNNING_TESTS=False)
    @patch("portal.services.locations.urlopen")
    @patch("portal.services.locations._throttle_request")
    def test_lookup_rejects_malformed_coordinates(self, throttle, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'[{"lat":"999","lon":"0"}]'
        urlopen.return_value = response
        with self.assertRaises(LocationResolutionError):
            resolve_location("invalid-place-test")

    @override_settings(RUNNING_TESTS=False)
    @patch("portal.services.locations.urlopen")
    @patch("portal.services.locations._throttle_request")
    def test_common_indian_search_areas_are_sent_as_explicit_india_queries(self, throttle, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'[{"lat":"28.6","lon":"77.2","display_name":"India"}]'
        urlopen.return_value = response

        for place in ("Noida", "Indirapuram", "Sector 62, Noida", "Delhi"):
            with self.subTest(place=place):
                self.assertEqual(resolve_location(place)["latitude"], 28.6)
        queries = [call.args[0].full_url for call in urlopen.call_args_list]
        self.assertEqual(len(queries), 4)
        self.assertTrue(all("countrycodes=in" in query and "format=jsonv2" in query for query in queries))
        self.assertTrue(all(call.kwargs["timeout"] == 10 for call in urlopen.call_args_list))
        self.assertIn("MediReach/1.0", urlopen.call_args_list[0].args[0].headers["User-agent"])

    @override_settings(RUNNING_TESTS=False)
    @patch("portal.services.locations.urlopen")
    @patch("portal.services.locations._throttle_request")
    def test_rate_limit_is_classified_and_same_query_is_not_retried_immediately(self, throttle, urlopen):
        urlopen.side_effect = HTTPError(
            "https://nominatim.openstreetmap.org/search", 429, "Too Many Requests", {"Retry-After": "30"}, None
        )
        with self.assertRaises(LocationResolutionError) as raised:
            resolve_location("Noida-rate-limit-test")
        self.assertEqual(raised.exception.reason, "rate_limited")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.retry_after, 30)
        with self.assertRaises(LocationResolutionError) as cached:
            resolve_location("Noida-rate-limit-test")
        self.assertEqual(cached.exception.reason, "rate_limited")
        urlopen.assert_called_once()

    @override_settings(RUNNING_TESTS=False)
    @patch("portal.services.locations.urlopen", side_effect=URLError(TimeoutError("timed out")))
    @patch("portal.services.locations._throttle_request")
    def test_timeout_is_distinguished_from_rate_limit(self, throttle, urlopen):
        with self.assertRaises(LocationResolutionError) as raised:
            resolve_location("timeout-test-area")
        self.assertEqual(raised.exception.reason, "timeout")

    @override_settings(RUNNING_TESTS=False)
    @patch("portal.services.locations.urlopen")
    @patch("portal.services.locations._throttle_request")
    def test_empty_geocoder_result_is_a_not_found_state(self, throttle, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b"[]"
        urlopen.return_value = response
        with self.assertRaises(LocationResolutionError) as raised:
            resolve_location("not-a-real-place-test")
        self.assertEqual(raised.exception.reason, "not_found")


class PatientChatJourneyTests(SimpleTestCase):
    @patch("portal.services.chat.discover_providers", return_value=[])
    def test_named_facility_search_preserves_name_and_arbitrary_location(self, discover):
        response, _ = respond("Find AIIMS near Delhi")
        self.assertEqual(response["intent"], "hospital_discovery")
        self.assertEqual(discover.call_args.kwargs["query"], "AIIMS")
        self.assertEqual(discover.call_args.kwargs["location"], "Delhi")
        self.assertTrue(discover.call_args.kwargs["include_osm"])

    @patch("portal.services.chat.discover_providers", return_value=[])
    def test_named_facility_no_match_is_not_replaced_with_unrelated_results(self, discover):
        response, _ = respond("Find AIIMS near Delhi")
        self.assertEqual(response["providers"], [])
        self.assertIn("No matching facility record was found for AIIMS", response["reply"])
        self.assertIn("did not substitute unrelated facilities", response["reply"])

    @patch("portal.services.chat.discover_providers")
    def test_geocoding_failure_is_explained_in_doctor_discovery(self, discover):
        def unresolved(**kwargs):
            kwargs["source_errors"].append({
                "source": "Location", "reason": "timeout", "status_code": None,
                "message": "Location search timed out. Please try again shortly.",
            })
            return []
        discover.side_effect = unresolved
        response, _ = respond("Find a dentist near Indirapuram")
        self.assertIn("Location search timed out", response["reply"])
        self.assertIn("stored address text only", response["reply"])

    @patch("portal.services.chat.discover_providers")
    def test_overpass_failure_is_explained_in_facility_discovery(self, discover):
        def rate_limited(**kwargs):
            kwargs["source_errors"].append({
                "source": "OpenStreetMap", "reason": "rate_limited", "status_code": 429,
                "retry_after": 30, "message": "Overpass facility search was rate-limited. Wait before retrying.",
            })
            return []
        discover.side_effect = rate_limited
        response, _ = respond("Find a hospital near Noida")
        self.assertIn("Overpass facility search was rate-limited", response["reply"])
        self.assertNotIn("area could not be resolved", response["reply"])

    @patch("portal.services.chat.discover_providers", return_value=[])
    def test_dentist_search_uses_shared_discovery_with_area(self, discover):
        response, _ = respond("Find a dentist near Sector 62, Noida")
        self.assertEqual(response["intent"], "doctor_discovery")
        self.assertEqual(discover.call_args.kwargs["specialty"], "Dentist")
        self.assertEqual(discover.call_args.kwargs["location"], "Sector 62, Noida")
        self.assertTrue(discover.call_args.kwargs["include_osm"])

    @patch("portal.services.chat.discover_providers", return_value=[{
        "result_id": "osm:node:12", "result_type": "osm_facility", "source": "OpenStreetMap",
        "facility_category": "dentist", "trust_label": "OpenStreetMap mapped — not independently verified",
    }])
    def test_mapped_dentist_is_presented_as_a_facility_not_a_doctor_profile(self, discover):
        response, _ = respond("Find a dentist near Indirapuram")
        self.assertEqual(response["doctors"], [])
        self.assertEqual(response["mapped_facilities"][0]["facility_category"], "dentist")
        self.assertIn("No individual doctor profile matched", response["reply"])
        self.assertIn("not verified doctor profiles", response["reply"])

    @patch("portal.services.chat.generate_general_reply")
    @patch("portal.services.chat.discover_providers")
    def test_specialty_explanation_is_useful_without_ai_or_provider_search(self, discover, ai):
        response, _ = respond("What is the difference between a cardiologist and a cardiac surgeon?")
        self.assertEqual(response["response_mode"], "curated")
        self.assertIn("heart and blood-vessel", response["reply"])
        self.assertIn("operations", response["reply"])
        self.assertIn("not a diagnosis", response["reply"])
        discover.assert_not_called()
        ai.assert_not_called()

    @patch("portal.services.chat.generate_general_reply")
    @patch("portal.services.chat.discover_providers")
    def test_emergency_response_precedes_provider_and_ai_calls(self, discover, ai):
        response, _ = respond("I have severe chest pain")
        self.assertEqual(response["intent"], "medical_emergency")
        self.assertEqual(response["emergency_number"], "112")
        self.assertTrue(any(action["href"] == "tel:112" for action in response["actions"]))
        discover.assert_not_called()
        ai.assert_not_called()

    def test_educational_chest_pain_question_is_not_an_emergency_alert(self):
        response, _ = respond("What are common causes of chest pain?")
        self.assertNotEqual(response["intent"], "medical_emergency")


class PatientJourneyFrontendSourceTests(SimpleTestCase):
    def test_map_uses_policy_compliant_osm_host_and_visible_attribution(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        script = (root / "static" / "portal" / "hospital-finder.js").read_text(encoding="utf-8")
        page = (root / "templates" / "portal" / "hospitals.html").read_text(encoding="utf-8")
        self.assertIn("https://tile.openstreetmap.org/{z}/{x}/{y}.png", script)
        self.assertIn("referrerPolicy: 'strict-origin-when-cross-origin'", script)
        self.assertNotIn("https://{s}.tile.openstreetmap.org", script)
        self.assertIn("OpenStreetMap</a> contributors", script)
        self.assertIn("https://www.openstreetmap.org/copyright", script)
        self.assertIn("Map tiles by OpenStreetMap contributors", page)
        self.assertIn("map-panel", page)
        self.assertIn("id=\"map-library-status\"", page)
        self.assertIn("id=\"location-resolution-status\"", page)
        self.assertIn("id=\"provider-search-status\"", page)

    def test_patient_search_forms_prioritize_specialty_and_area(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        doctors = (root / "templates" / "portal" / "doctors.html").read_text(encoding="utf-8")
        hospitals = (root / "templates" / "portal" / "hospitals.html").read_text(encoding="utf-8")
        self.assertIn("name=\"specialty\"", doctors)
        self.assertIn("name=\"location\"", doctors)
        self.assertIn("Area, city or PIN code", doctors)
        self.assertIn("Area, city or PIN code", hospitals)
        self.assertIn("Facility type (optional)", hospitals)
        self.assertIn("<details", doctors)
        self.assertIn("<details", hospitals)
