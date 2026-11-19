"""Checks for the shared conditions checker (tools/conditions.py).

Run: python3 -B -m unittest discover -s tools -p 'test_*.py'
Uses two made-up searchers, never your own criteria: a New York searcher (the job-search test fixture)
and the sample person, Riley, in Columbus, Ohio.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as C

REPO = Path(__file__).resolve().parent.parent
NYC = REPO / "job-search" / "tests" / "fixtures" / "criteria-nyc.yaml"
RILEY = REPO / "examples" / "sample-person" / "career" / "search-criteria.yaml"
COND = C.load_conditions(NYC)


class SharedConditions(unittest.TestCase):
    def result(self, location, workplace="Hybrid", travel=None, url=None):
        return C.check(location, workplace, COND, travel, url)[0]

    def test_fifty_mile_radius(self):
        inside = ["New York, NY", "Rye, NY", "Yonkers, NY", "Tarrytown, New York, United States", "Stamford, CT",
                  "Morristown, NJ", "Princeton, New Jersey", "Hoboken, NJ",
                  "Brooklyn", "New York City", "NYC", "New York", "Miami or New York City", "Mahwah, New Jersey, United States"]
        outside = ["Albany, New York", "New Haven, CT", "Cherry Hill, NJ", "Danbury, CT", "Philadelphia, PA",
                   "San Francisco, CA", "London, United Kingdom", "Berlin, Germany", "California"]
        for loc in inside:
            self.assertEqual(self.result(loc), "pass", loc)
        for loc in outside:
            self.assertEqual(self.result(loc), "fail", loc)

    def test_unplaceable_or_partial_places_are_asked(self):
        for loc in ["Long Island", "New Jersey", "Springfield", "", "Smalltownville, NY"]:
            self.assertEqual(self.result(loc), "unknown", loc)

    def test_remote_us_passes_and_abroad_asks(self):
        for loc in ["United States", "Remote", "", "Austin, TX", "Seattle or Indianapolis", "New York, NY"]:
            self.assertEqual(self.result(loc, "Remote"), "pass", loc)
        for loc in ["Bangalore, India", "Toronto, Ontario", "Dublin, Ireland", "Canada", "Berlin, Germany"]:
            self.assertEqual(self.result(loc, "Remote"), "unknown", loc)

    def test_portland_or_is_a_state_not_a_conjunction(self):
        self.assertEqual(C.segments("Portland, OR or New York, NY"), ["Portland, OR", "New York, NY"])
        self.assertEqual(self.result("Portland, OR or New York, NY"), "pass")

    def test_state_from_hiringcafe_url(self):
        url = "https://hiringcafe.com/job/sr-product-strategy-manager-zelis-morristown-new-jersey-zrbm4?utm_source=x"
        result, reasons = C.check("Morristown or Atlanta", "Hybrid", COND, url=url)
        self.assertEqual(result, "pass")
        self.assertIn("posting URL", " ".join(reasons))

    def test_travel_above_limit_asks(self):
        self.assertEqual(self.result("New York, NY", travel=50), "pass")
        self.assertEqual(self.result("New York, NY", travel=70), "unknown")

    def test_cli_for_stage1(self):
        out = subprocess.run([sys.executable, str(Path(C.__file__)), "--location", "Rye, NY", "--workplace", "hybrid",
                              "--criteria", str(NYC)], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)["result"], "pass")


class AnyCenter(unittest.TestCase):
    """The product measures from the user's own center, anywhere in the US."""

    def setUp(self):
        self.cond = C.load_conditions(RILEY)

    def result(self, location, workplace="Hybrid", cond=None):
        return C.check(location, workplace, cond or self.cond)[0]

    def test_riley_in_columbus(self):
        for loc in ["Columbus, OH", "Dublin, OH", "Westerville, Ohio", "Grove City, OH", "Central Ohio"]:
            self.assertEqual(self.result(loc), "pass", loc)
        for loc in ["Cleveland, OH", "Cincinnati, OH", "Pittsburgh, PA", "New York, NY"]:
            self.assertEqual(self.result(loc), "fail", loc)
        # A bare "Dublin" reads as Ireland; a posting for Dublin, Ohio names the state.
        self.assertEqual(self.result("Dublin", "Remote"), "unknown")

    def test_reason_names_the_center(self):
        _, reasons = C.check("Dublin, OH", "Hybrid", self.cond)
        self.assertIn("from Columbus, OH", reasons[0])

    def test_center_by_coordinates(self):
        cond = {"center_lat": 39.96, "center_lon": -83.0, "radius_miles": 40}
        self.assertEqual(self.result("Dublin, OH", cond=cond), "pass")

    def test_no_center_asks_instead_of_guessing(self):
        empty = C.load_conditions(REPO / "career" / "search-criteria.yaml")
        self.assertEqual(self.result("Columbus, OH", cond=empty), "unknown")
        self.assertEqual(self.result("United States", "Remote", cond=empty), "pass")

    def test_workplace_the_user_does_not_accept_fails(self):
        cond = dict(self.cond, acceptable_workplaces=["hybrid", "onsite"])
        self.assertEqual(self.result("United States", "Remote", cond=cond), "fail")
        self.assertEqual(self.result("Columbus, OH", "On-site", cond=cond), "pass")

    def test_place_list_covers_every_state(self):
        states = {k.rsplit("|", 1)[1] for k in C.gazetteer()}
        self.assertTrue(set(C.STATES.values()) <= states)


if __name__ == "__main__":
    unittest.main()
