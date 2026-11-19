"""Core validation on the schema 1.3 sample run (one job per status)."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pipeline import render_cards, summary, validate  # noqa: E402


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.run = json.loads((ROOT / "tests/fixtures/sample_run.json").read_text())

    def errs(self, run):
        return validate(run)

    def test_fixture_valid(self):
        self.assertEqual(self.errs(self.run), [])

    def test_one_job_per_status(self):
        s = summary(self.run)
        self.assertEqual([s[k] for k in ("eligible", "needs_verification", "deprioritized", "excluded", "evaluation_error")],
                         [1, 1, 1, 1, 1])
        self.assertEqual((s["discovered"], s["unique"], s["review_queue"]), (6, 5, 2))

    def test_fixture_renders(self):
        self.assertIn("Example Kitchen Co", render_cards(self.run))

    def test_duplicate_rejected(self):
        r = copy.deepcopy(self.run)
        r["jobs"].append(copy.deepcopy(r["jobs"][0]))
        r["discovered_count"] += 1
        self.assertTrue(any("duplicate ID" in e for e in self.errs(r)))

    def test_score_tamper_rejected(self):
        r = copy.deepcopy(self.run)
        r["jobs"][0]["fit_percent"] = 99
        self.assertTrue(any("computed" in e for e in self.errs(r)))

    def test_exclusion_requires_provenance(self):
        r = copy.deepcopy(self.run)
        r["jobs"][3]["exclusion"] = None
        self.assertTrue(any("documented exclusion" in e for e in self.errs(r)))
        r["jobs"][3]["exclusion"] = {"requirement_quote": "q", "reason": "r", "basis": "user_confirmed_unmet"}
        self.assertTrue(any("invalid exclusion basis" in e for e in self.errs(r)))

    def test_competency_rules(self):
        r = copy.deepcopy(self.run)
        reqs = r["jobs"][0]["requirements"]
        reqs[1]["competency_id"] = reqs[0]["competency_id"]
        self.assertTrue(any("duplicate competency_id" in e for e in self.errs(r)))
        r = copy.deepcopy(self.run)
        r["jobs"][0]["requirements"][0]["evidence_note"] = ""
        self.assertTrue(any("evidence_note" in e for e in self.errs(r)))

    def test_unknown_condition_not_eligible(self):
        r = copy.deepcopy(self.run)
        r["jobs"][0]["requirements"][-1]["condition_status"] = "unknown"
        self.assertTrue(any("unresolved" in e for e in self.errs(r)))


if __name__ == "__main__":
    unittest.main()
