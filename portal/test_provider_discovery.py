import json
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from portal.services.chat import respond
from portal.services.resources import discover_providers
from portal.services.osm_facilities import FacilityDiscoveryError
from portal.services.locations import LocationResolutionError


class SharedProviderDiscoveryTests(SimpleTestCase):
    def setUp(self):
        self.doctor = {
            "id": 12, "name": "Dr Example", "city": "Pune", "specialty": "Cardiology",
            "specialties": ["Cardiology"], "provider_status": "unverified",
            "trust_label": "Unverified", "sources": [], "contacts": [],
            "facilities": [{"latitude": 18.5, "longitude": 73.8}],
        }
        self.hospital = {
            "id": 7, "name": "Example Facility", "city": "Pune", "address": "Example Road",
            "facility_type": "clinic", "latitude": 18.5, "longitude": 73.8,
            "distance_km": 1.2, "verification_status": "unverified", "trust_label": "Unverified",
            "sources": [], "contacts": [], "services": [],
        }
        self.osm = {
            "osm_type": "node", "osm_id": 7, "facility_category": "clinic",
            "latitude": 18.5, "longitude": 73.8, "source_name": "OpenStreetMap",
            "source_url": "https://www.openstreetmap.org/node/7",
            "trust_label": "OpenStreetMap mapped — not independently verified",
        }

    @patch("portal.services.resources.search_mapped_facilities")
    @patch("portal.services.resources.search_hospitals")
    @patch("portal.services.resources.search_doctors")
    def test_sources_remain_separate_and_results_have_stable_normalized_ids(self, doctors, hospitals, osm):
        doctors.return_value = [self.doctor]
        hospitals.return_value = [self.hospital]
        osm.return_value = [self.osm, self.osm]
        results = discover_providers(
            latitude=18.5, longitude=73.8, include_osm=True, result_types=("doctor", "hospital"),
        )
        self.assertEqual(len(results), 3)
        self.assertEqual({item["result_id"] for item in results}, {
            "managed:doctor:12", "managed:hospital:7", "osm:node:7",
        })
        mapped = next(item for item in results if item["source"] == "OpenStreetMap")
        managed = next(item for item in results if item["source"] == "MediReach" and item["result_type"] == "hospital")
        self.assertEqual(mapped["trust_category"], "mapped_unverified")
        self.assertEqual(managed["trust_category"], "unverified")
        self.assertNotEqual(mapped["result_id"], managed["result_id"])

    @patch("portal.services.resources.search_mapped_facilities")
    @patch("portal.services.resources.search_hospitals")
    def test_filters_apply_only_to_data_supported_by_each_source(self, hospitals, osm):
        hospitals.side_effect = [[self.hospital], []]
        osm.return_value = [self.osm]
        results = discover_providers(
            result_types="hospital", latitude=18.5, longitude=73.8,
            include_osm=True, facility_type="clinic", source_category="openstreetmap",
        )
        self.assertEqual([item["source"] for item in results], ["OpenStreetMap"])
        no_matches = discover_providers(
            result_types="hospital", latitude=18.5, longitude=73.8,
            include_osm=True, specialty="cardiology",
        )
        self.assertEqual(no_matches, [])

    @patch("portal.services.resources.search_mapped_facilities")
    @patch("portal.services.resources.search_hospitals", return_value=[])
    def test_missing_osm_fields_are_not_fabricated(self, _hospitals, osm):
        osm.return_value = [self.osm]
        result = discover_providers(
            result_types="hospital", latitude=18.5, longitude=73.8, include_osm=True,
        )[0]
        self.assertNotIn("name", result)
        self.assertNotIn("address", result)
        self.assertNotIn("specialties", result)
        self.assertNotIn("services", result)
        self.assertEqual(result["contact_information"], [])

    @patch("portal.services.resources.search_hospitals")
    @patch("portal.services.resources.search_mapped_facilities")
    def test_osm_specialty_filter_requires_an_explicit_specialty_tag(self, osm, hospitals):
        hospitals.return_value = []
        tagged = {**self.osm, "specialties": ["cardiology"]}
        osm.return_value = [tagged]
        results = discover_providers(
            result_types="hospital", latitude=18.5, longitude=73.8,
            include_osm=True, specialty="cardio",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["specialties"], ["cardiology"])

    @patch("portal.services.resources.search_hospitals")
    def test_distance_filter_excludes_managed_records_without_nearby_coordinates(self, hospitals):
        far_record = {**self.hospital, "distance_km": 25.0}
        hospitals.return_value = [far_record]
        self.assertEqual(discover_providers(
            result_types="hospital", latitude=18.5, longitude=73.8, radius_km=5,
        ), [])

    @patch("portal.services.resources.search_mapped_facilities", side_effect=FacilityDiscoveryError("Map service busy"))
    @patch("portal.services.resources.search_hospitals")
    def test_osm_failure_keeps_managed_results_and_reports_source_error(self, hospitals, _osm):
        hospitals.return_value = [self.hospital]
        errors = []
        results = discover_providers(
            result_types="hospital", latitude=18.5, longitude=73.8,
            include_osm=True, source_errors=errors,
        )
        self.assertEqual([item["source"] for item in results], ["MediReach"])
        self.assertEqual(errors[0]["source"], "OpenStreetMap")

    @patch("portal.services.resources.search_hospitals", return_value=[])
    @patch("portal.services.resources.search_mapped_facilities")
    @patch("portal.services.resources.resolve_location", side_effect=LocationResolutionError(
        "Location search was rate-limited.", reason="rate_limited", status_code=429, retry_after=30,
    ))
    def test_geocoder_rate_limit_is_not_reported_as_an_overpass_failure(self, resolve, mapped, hospitals):
        errors = []
        results = discover_providers(result_types="hospital", location="Noida", include_osm=True, source_errors=errors)
        self.assertEqual(results, [])
        mapped.assert_not_called()
        self.assertEqual(errors[0]["source"], "Location")
        self.assertEqual(errors[0]["reason"], "rate_limited")
        self.assertEqual(errors[0]["status_code"], 429)
        self.assertEqual(errors[0]["retry_after"], 30)

    @patch("portal.services.resources.search_hospitals", return_value=[])
    @patch("portal.services.resources.search_mapped_facilities", side_effect=FacilityDiscoveryError(
        "Overpass was rate-limited.", reason="rate_limited", status_code=429, retry_after=45,
    ))
    @patch("portal.services.resources.resolve_location", return_value={"latitude": 28.5, "longitude": 77.3})
    def test_overpass_rate_limit_is_reported_separately_from_geocoding(self, resolve, mapped, hospitals):
        errors = []
        discover_providers(result_types="hospital", location="Noida", include_osm=True, source_errors=errors)
        self.assertEqual(errors[0]["source"], "OpenStreetMap")
        self.assertEqual(errors[0]["reason"], "rate_limited")
        self.assertEqual(errors[0]["status_code"], 429)

    @patch("portal.services.chat.discover_providers")
    def test_chat_uses_shared_discovery_and_separates_mapped_results(self, discovery):
        mapped = {**self.osm, "result_id": "osm:node:7", "result_type": "osm_facility", "source": "OpenStreetMap"}
        discovery.return_value = [mapped]
        response, _ = respond("Find hospitals near me", latitude=18.5, longitude=73.8)
        self.assertEqual(response["mapped_facilities"], [mapped])
        self.assertEqual(response["hospitals"], [])
        self.assertIn("not independently verified", response["reply"])
        self.assertIn("open or available", response["reply"])
        self.assertTrue(discovery.call_args.kwargs["include_osm"])

    def test_discovery_api_uses_post_json_and_keeps_source_labels(self):
        result = {**self.osm, "result_id": "osm:node:7", "result_type": "osm_facility", "source": "OpenStreetMap"}
        with patch("portal.views.discover_providers", return_value=[result]) as discovery:
            response = self.client.post(
                reverse("api_provider_discovery"),
                data=json.dumps({
                    "result_types": ["hospital"], "latitude": 18.5, "longitude": 73.8,
                    "radius_km": 5, "include_osm": True,
                }),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["source"], "OpenStreetMap")
        self.assertTrue(discovery.call_args.kwargs["include_osm"])

