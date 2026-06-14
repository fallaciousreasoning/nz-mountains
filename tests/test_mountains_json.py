import json
import re
from pathlib import Path
from unittest import TestCase

MOUNTAINS_JSON = Path(__file__).resolve().parent.parent / "mountains.json"
BASE_URL = "https://climbnz.org.nz"

MIN_MOUNTAINS = 1600
MIN_WITH_LATLNG = 1600
MIN_LATLNG_FRACTION = 0.95
MIN_ROUTES = 2000
MIN_MOUNTAINS_WITH_ROUTES = 900

MOUNTAIN_FIELDS = {
    "link", "name", "altitude", "access", "description",
    "latlng", "routes", "places", "image", "images",
}
ROUTE_FIELDS = {
    "link", "name", "grade", "topo_ref", "image", "images", "length",
    "pitches", "quality", "bolts", "natural_pro", "description", "ascent",
}
PITCH_FIELDS = {
    "alpine", "commitment", "mtcook", "aid", "ice", "mixed", "length",
    "bolts", "trad", "ewbank", "description",
}

ALTITUDE_RE = re.compile(r"^\d+m$")

# Spot checks for well-known entries that should stay stable.
SPOT_CHECKS = {
    "https://climbnz.org.nz/nz/si/aoraki-tai-poutini/kirikirikatata-mt-cook-range/aoraki-mt-cook": {
        "name": "Aoraki Mt Cook",
        "altitude": "3724m",
        "latlng": ("-43.5955671", "170.14219572"),
    },
    "https://climbnz.org.nz/castle-mount": {
        "name": "Pariroa Castle Mount",
        "latlng": ("-44.84780003", "167.77882903"),
        "min_routes": 1,
    },
}


def load_mountains():
    with MOUNTAINS_JSON.open() as f:
        return json.load(f)


def parse_latlng(latlng):
    if latlng is None:
        return None
    if not isinstance(latlng, list) or len(latlng) != 2:
        raise ValueError(f"expected [lat, lon], got {latlng!r}")
    lat = float(latlng[0])
    lon = float(latlng[1])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"lat/lon out of range: {latlng!r}")
    return lat, lon


class MountainsJsonTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mountains = load_mountains()

    def test_file_exists_and_parses(self):
        self.assertTrue(MOUNTAINS_JSON.is_file())
        self.assertIsInstance(self.mountains, dict)
        self.assertGreater(len(self.mountains), 0)

    def test_minimum_mountain_count(self):
        self.assertGreaterEqual(len(self.mountains), MIN_MOUNTAINS)

    def test_mountain_records(self):
        empty_names = []
        bad_links = []
        bad_altitudes = []
        bad_latlng = []

        for url, mountain in self.mountains.items():
            missing = MOUNTAIN_FIELDS - mountain.keys()
            self.assertFalse(missing, f"{url} missing fields: {missing}")

            self.assertEqual(mountain["link"], url)
            if not url.startswith(f"{BASE_URL}/"):
                bad_links.append(url)

            if not mountain["name"]:
                empty_names.append(url)
            elif mountain["altitude"] is not None and not ALTITUDE_RE.match(mountain["altitude"]):
                bad_altitudes.append((url, mountain["altitude"]))

            if mountain["latlng"] is not None:
                try:
                    parse_latlng(mountain["latlng"])
                except ValueError as err:
                    bad_latlng.append(f"{url}: {err}")

            self.assertIsInstance(mountain["routes"], list)
            self.assertIsInstance(mountain["places"], list)
            self.assertIsInstance(mountain["images"], list)

        self.assertEqual(empty_names, [])
        self.assertEqual(bad_links, [])
        self.assertEqual(bad_altitudes, [])
        self.assertEqual(bad_latlng, [])

    def test_latlng_coverage(self):
        with_latlng = sum(1 for m in self.mountains.values() if m["latlng"] is not None)
        fraction = with_latlng / len(self.mountains)

        self.assertGreaterEqual(with_latlng, MIN_WITH_LATLNG)
        self.assertGreaterEqual(fraction, MIN_LATLNG_FRACTION)

    def test_route_records(self):
        route_count = 0
        mountains_with_routes = 0
        bad_routes = []

        for mountain in self.mountains.values():
            if mountain["routes"]:
                mountains_with_routes += 1

            for route in mountain["routes"]:
                route_count += 1
                missing = ROUTE_FIELDS - route.keys()
                if missing:
                    bad_routes.append(f"{route.get('link')}: missing {missing}")
                    continue

                if not route["name"]:
                    bad_routes.append(f"{route.get('link')}: empty name")
                if not route["link"].startswith(f"{BASE_URL}/"):
                    bad_routes.append(f"{route.get('link')}: bad link")

                for pitch in route["pitches"]:
                    missing_pitch = PITCH_FIELDS - pitch.keys()
                    if missing_pitch:
                        bad_routes.append(f"{route.get('link')}: pitch missing {missing_pitch}")

        self.assertEqual(bad_routes, [])
        self.assertGreaterEqual(route_count, MIN_ROUTES)
        self.assertGreaterEqual(mountains_with_routes, MIN_MOUNTAINS_WITH_ROUTES)

    def test_spot_checks(self):
        for url, expected in SPOT_CHECKS.items():
            self.assertIn(url, self.mountains, f"missing expected mountain {url}")
            mountain = self.mountains[url]

            for field, value in expected.items():
                if field == "min_routes":
                    self.assertGreaterEqual(len(mountain["routes"]), value)
                elif field == "latlng":
                    self.assertEqual(tuple(mountain["latlng"]), value)
                else:
                    self.assertEqual(mountain[field], value)
