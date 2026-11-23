import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase
from django.urls import reverse

from portal.services import osm_facilities
from portal.services.osm_facilities import (
    FacilityDiscoveryError,
    discover_facilities,
    normalize_element,
    validate_search,
)


class OSMFacilityServiceTests(SimpleTestCase):
    def setUp(self):
        osm_facilities._cache.clear()

    def response(self, payload):
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        return response

    def test_coordinate_and_radius_ranges_are_enforced(self):
        self.assertEqual(validate_search("18.5", "73.8", "5"), (18.5, 73.8, 5.0))
        for values in ((91, 73, 5), (18, 181, 5), (18, 73, 20.1), (18, 73, 0), (True, 73, 5)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                validate_search(*values)

    def test_normalization_preserves_only_supplied_fields_and_safe_links(self):
        record = normalize_element({
            "type": "node", "id": 123, "lat": 18.5, "lon": 73.8,
            "tags": {
                "healthcare": "laboratory", "addr:city": "Pune", "phone": "+91 123",
                "website": "javascript:alert(1)",
            },
        })
        self.assertNotIn("name", record)
        self.assertNotIn("website", record)
        self.assertEqual(record["facility_category"], "laboratory")
        self.assertEqual(record["address"], {"city": "Pune"})
        self.assertEqual(record["phone"], "+91 123")
        self.assertEqual(record["source_url"], "https://www.openstreetmap.org/node/123")
        self.assertEqual(record["trust_label"], "OpenStreetMap mapped — not independently verified")

    def test_way_center_and_valid_website_are_normalized(self):
        record = normalize_element({
            "type": "way", "id": 45, "center": {"lat": 19, "lon": 72},
            "tags": {"amenity": "clinic", "name": "Clinic", "website": "https://example.org"},
        })
        self.assertEqual((record["latitude"], record["longitude"]), (19.0, 72.0))
        self.assertEqual(record["facility_category"], "clinic")
        self.assertEqual(record["website"], "https://example.org")

    @patch("portal.services.osm_facilities.urlopen")
    def test_timeout_and_rate_limit_errors_are_reported_safely(self, mocked_urlopen):
        mocked_urlopen.side_effect = URLError("timed out")
        with self.assertRaises(FacilityDiscoveryError):
            discover_facilities(18.5, 73.8, 5)
        mocked_urlopen.side_effect = TimeoutError("connection timeout")
        with self.assertRaises(FacilityDiscoveryError):
            discover_facilities(18.5, 73.8, 5)
        mocked_urlopen.side_effect = HTTPError(osm_facilities.OVERPASS_URL, 429, "rate limited", {}, None)
        with self.assertRaises(FacilityDiscoveryError):
            discover_facilities(18.5, 73.8, 6)

    @patch("portal.services.osm_facilities.urlopen")
    def test_overpass_rate_limit_exposes_retry_status_without_coordinates(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            osm_facilities.OVERPASS_URL, 429, "rate limited", {"Retry-After": "45"}, None
        )
        with self.assertRaises(FacilityDiscoveryError) as raised:
            discover_facilities(28.5, 77.3, 5)
        self.assertEqual(raised.exception.reason, "rate_limited")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.retry_after, 45)
        self.assertNotIn("28.5", str(raised.exception))

    @patch("portal.services.osm_facilities.urlopen")
    def test_malformed_response_is_rejected(self, mocked_urlopen):
        mocked_urlopen.return_value = self.response({"unexpected": []})
        with self.assertRaises(FacilityDiscoveryError):
            discover_facilities(18.5, 73.8, 5)

    @patch("portal.services.osm_facilities.urlopen")
    def test_same_query_uses_short_in_process_cache(self, mocked_urlopen):
        mocked_urlopen.return_value = self.response({"elements": [
            {"type": "node", "id": 1, "lat": 18.5, "lon": 73.8, "tags": {"amenity": "hospital"}},
        ]})
        first = discover_facilities(18.5, 73.8, 5)
        second = discover_facilities(18.5, 73.8, 5)
        self.assertEqual(first, second)
        mocked_urlopen.assert_called_once()


class OSMFacilityEndpointTests(SimpleTestCase):
    def test_post_endpoint_validates_coordinates_and_returns_attributed_mapped_results(self):
        with patch("portal.views.search_mapped_facilities", return_value=[{
            "osm_type": "node", "osm_id": 7,
            "trust_label": "OpenStreetMap mapped — not independently verified",
        }]) as search:
            response = self.client.post(
                reverse("api_osm_facilities"),
                data=json.dumps({"latitude": 18.5, "longitude": 73.8, "radius_km": 5}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "OpenStreetMap")
        self.assertEqual(response.json()["results"][0]["osm_id"], 7)
        self.assertEqual(search.call_args.args, (18.5, 73.8, 5))

    def test_endpoint_rejects_missing_coordinates_and_wrong_method(self):
        invalid = self.client.post(reverse("api_osm_facilities"), data="{}", content_type="application/json")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.get(reverse("api_osm_facilities")).status_code, 405)
