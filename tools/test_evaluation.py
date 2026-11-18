"""Checks for the shared evaluation engine (tools/evaluation.py) and jd_key.py assemble.

Run: python3 -B -m unittest discover -s tools -p 'test_*.py'
The command-line checks run against a temporary copy of the fictional sample person's
record (examples/sample-person), never your own record.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluation as E
import jd_key

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "examples" / "sample-person"


def setUpModule():
    global ROOT, JD_KEY
    ROOT = Path(tempfile.mkdtemp())
    shutil.copytree(SAMPLE / "career", ROOT / "career")
    (ROOT / "tools").mkdir()
    for script in (REPO / "tools").glob("*.py"):
        shutil.copy2(script, ROOT / "tools" / script.name)
    JD_KEY = str(ROOT / "tools" / "jd_key.py")


def tearDownModule():
    shutil.rmtree(ROOT, ignore_errors=True)


class SharedMath(unittest.TestCase):
    def test_score_credit_is_quarter_steps(self):
        for score, expected in [(0, 0), (1, 25), (2, 50), (3, 75), (4, 100)]:
            self.assertEqual(E.assess([{"competency_id": "a", "kind": "want", "score": score}])["functional_fit"], expected)
            self.assertEqual(jd_key.fit_baseline({"Want-1": score}, set()), E.assess(E.from_tags({"Want-1": score}))["baseline_fit"])
        # Only the current policy exists; earlier ones were removed (Git history keeps them).
        self.assertEqual(E.POLICIES, {"shared-2"})
        for old in ("shared-1", "shared-9"):
            with self.assertRaises(ValueError): E.assess([{"competency_id": "a", "kind": "want", "score": 2}], policy=old)

    def test_nice_traits_context_half_and_conditions_excluded(self):
        scores = {"Want-1": 4, "Nice-1": 0, "About-1": 2, "Want-2": 3, "Cond-1": "fail"}
        asks = E.from_tags(scores, {"Want-2"})
        result = E.assess(asks)
        self.assertEqual(result["functional_fit"], 65)  # (1 + 0 + 0.25 + 0.375) / 2.5
        self.assertEqual(jd_key.fit_baseline(scores, {"Want-2"}), result["baseline_fit"])

    def test_adjustments_require_reason_are_bounded_and_clamped(self):
        ask = [{"competency_id": "a", "kind": "want", "score": 3}]
        self.assertEqual(E.assess(ask, 5, "Material uncertainty in outcome attribution.")["functional_fit"], 80)
        for points, reason in [(6, "x"), (-6, "x"), (float("nan"), "x"), (float("inf"), "x"), (3, None)]:
            with self.assertRaises(ValueError): E.assess(ask, points, reason)
        self.assertEqual(E.assess([dict(ask[0], score=4)], 5, "x")["functional_fit"], 100)
        with self.assertRaises(ValueError): E.assess([], 1, "x")

    def test_merge_preserves_tags_but_counts_once(self):
        scores = {"Want-1": 3, "Do-1": 3, "Nice-1": 0}
        asks = E.from_tags(scores, groups={"delivery": ["Want-1", "Do-1"], "optional": ["Nice-1"]})
        self.assertEqual(len(asks), 2)
        self.assertEqual(asks[0]["source_tags"], ["Want-1", "Do-1"])
        self.assertEqual(E.assess(asks)["functional_fit"], 50)
        for groups in [{"a": ["Want-1"]}, {"a": ["Want-1", "Want-1"]}, {"a": ["Want-1", "Nice-1"], "b": ["Do-1"]}]:
            with self.assertRaises(ValueError): E.from_tags(scores, groups=groups)

    def test_kind_comes_from_source_tags(self):
        self.assertEqual(E.kind_for_tags(["Nice-1", "Want-2"]), "want")
        self.assertEqual(E.kind_for_tags(["Do-1", "Nice-1"]), "do")
        self.assertEqual(E.kind_for_tags(["Want-2"], {"Want-2"}), "trait")
        self.assertIsNone(E.check_kind("trait", ["Want-1"]))
        self.assertIsNone(E.check_kind("want", ["Want-1", "Do-1"]))
        self.assertTrue(E.check_kind("want", ["Nice-1"]))
        for tags in (["Cond-1"], ["Want-1", "Cond-1"], ["Bogus-1"], []):
            with self.assertRaises(ValueError): E.kind_for_tags(tags)

    def test_stage1_cli_writes_explicit_baseline_and_adjustment(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "tags.json").write_text(json.dumps({"Want-1": {"text": "Lead delivery.", "short": "Lead delivery."}}))
            (d / "scores.txt").write_text("Want-1 3 NW-EXP-001\n")
            (d / "body.md").write_text("{Want-1'}\n")
            result = subprocess.run([sys.executable, JD_KEY, "assemble", str(d / "tags.json"), "--scores", str(d / "scores.txt"), "--adjustment", "-2", "--adjustment-reason", "Outcome evidence is limited.", "--assessment-out", str(d / "assessment.json"), str(d / "body.md")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = json.loads((d / "assessment.json").read_text())
            self.assertEqual(saved["functional_fit"], 73)
            self.assertEqual(saved["label"], E.STRETCH)
            self.assertEqual(saved["requirements_met"], {"met": 1, "total": 1})
            self.assertEqual(saved["requirements"][0]["record_ids"], ["NW-EXP-001"])
            self.assertEqual(saved["evaluation_policy"], E.POLICY)
            self.assertIn("adjustment -2", result.stderr)

    def test_stage1_scores_need_known_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "tags.json").write_text(json.dumps({"Want-1": {"text": "Lead delivery.", "short": None}}))
            (d / "body.md").write_text("")
            def run(line):
                (d / "s.txt").write_text(line)
                return subprocess.run([sys.executable, JD_KEY, "assemble", str(d / "tags.json"),
                                       "--scores", str(d / "s.txt"), str(d / "body.md")], capture_output=True, text=True)
            for line, ok in [("Want-1 2\n", False), ("Want-1 2 NOT-A-RECORD\n", False), ("Want-1 0\n", True),
                             ("Want-1 2 NW-EXP-001,NW-OUT-001\n", True)]:
                self.assertEqual(run(line).returncode == 0, ok, line)


    def test_sample_ids_are_found_and_templates_ignored(self):
        ids = E.career_ids(ROOT)
        self.assertIn("NW-EXP-001", ids)
        self.assertEqual(E.career_ids(REPO), set(), "the shipped skeleton holds no record IDs")


class Labels(unittest.TestCase):
    def test_bands(self):
        self.assertEqual([E.label(f) for f in (100, 75, 74, 60, 59, 0)],
                         [E.PROMISING, E.PROMISING, E.STRETCH, E.STRETCH, E.DEPRIORITIZE, E.DEPRIORITIZE])
        self.assertIsNone(E.label(None))

    def test_gates_move_at_most_one_level(self):
        self.assertEqual(E.label(90, critical=1), E.STRETCH)
        self.assertEqual(E.label(90, unresolved=1), E.STRETCH)
        self.assertEqual(E.label(90, critical=1, stale=True), E.STRETCH)
        self.assertEqual(E.label(65, critical=1), E.STRETCH)
        self.assertEqual(E.label(65, stale=True), E.DEPRIORITIZE)
        self.assertEqual(E.label(95, condition_failed=True), E.DEPRIORITIZE)
        self.assertEqual(E.label(95, knocked_out=True), E.DEPRIORITIZE)
        self.assertEqual(E.label(None, knocked_out=True), E.DEPRIORITIZE)

    def test_requirements_met_counts_want_tags(self):
        asks = E.from_tags({"Want-1": 4, "Want-2": 2, "Want-3": 1, "Do-1": 0, "Nice-1": 4},
                           groups={"a": ["Want-1"], "b": ["Want-2"], "c": ["Want-3"], "d": ["Do-1"], "e": ["Nice-1"]})
        self.assertEqual(E.gap_counts(asks), (1, 1, 1, 3))
        decided = E.decide(asks, 80, ["pass", "unknown"])
        self.assertEqual((decided["label"], decided["requirements_met"]), (E.STRETCH, {"met": 1, "total": 3}))
        self.assertEqual(E.decide(asks, 80, ["fail"])["label"], E.DEPRIORITIZE)


if __name__ == "__main__":
    unittest.main()
