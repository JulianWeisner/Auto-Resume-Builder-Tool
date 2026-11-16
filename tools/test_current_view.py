"""Regression checks for the career view's discovery modes (--index, --search, --ids --related).

Run: python3 -B -m unittest discover -s tools -p 'test_*.py'
Runs against a temporary copy of the fictional sample person's record
(examples/sample-person), never your own record.
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "examples" / "sample-person"


def setUpModule():
    global ROOT, current_view
    ROOT = Path(tempfile.mkdtemp())
    shutil.copytree(SAMPLE / "career", ROOT / "career")
    (ROOT / "tools").mkdir()
    for script in (REPO / "tools").glob("*.py"):
        shutil.copy2(script, ROOT / "tools" / script.name)
    spec = importlib.util.spec_from_file_location("sample_current_view", ROOT / "tools" / "current_view.py")
    current_view = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(current_view)


def tearDownModule():
    shutil.rmtree(ROOT, ignore_errors=True)


class CurrentViewTests(unittest.TestCase):
    def run_view(self, *args):
        return subprocess.check_output([sys.executable, "-B", str(ROOT / "tools/current_view.py"), *args], text=True)

    def test_collections_are_discovered(self):
        self.assertEqual(sorted(current_view.COLLECTIONS), [
            "career/education/records.md", "career/experience/records.md",
            "career/northwind/experiences.md", "career/northwind/roles.md"])

    def test_index_covers_every_experience(self):
        output = self.run_view("--index")
        expected = [rec["id"] for path in current_view.COLLECTIONS for rec in current_view.records(path)
                    if rec.get("record_type") in ("experience", "credentials")]
        found = [line.split(" | ", 1)[0] for line in output.splitlines() if " | " in line]
        self.assertTrue(set(expected) <= set(found))
        self.assertEqual(len(found), len(set(found)))
        self.assertLess(len(output.split()), len(self.run_view().split()))

    def test_search_finds_experiences_and_outcomes(self):
        search = self.run_view("--search", "dock-to-stock")
        self.assertIn("NW-EXP-001", search)
        outcome = self.run_view("--search", "second site was not included")
        self.assertIn("NW-OUT-001", outcome)
        self.assertIn("NW-EXP-002", outcome)

    def test_related_retrieval_keeps_roles_outcomes_and_metric_limits(self):
        output = self.run_view("--ids", "NW-EXP-002", "--related")
        self.assertIn("id: NW-EXP-002", output)
        self.assertIn("id: NW-OUT-001", output)
        self.assertIn("id: NW-ROLE-003", output)
        self.assertIn("id: NW-EXP-001", output)  # related experience
        self.assertIn("the second site was not included", output)

    def test_unknown_id_fails_before_printing_evidence(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/current_view.py"),
                                 "--ids", "UNKNOWN"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_index_flags_limits_and_formats_dates(self):
        index = self.run_view("--index")
        lines = {line.split(" | ")[0]: line for line in index.splitlines() if " | " in line}
        # A claim whose qualifier lives on its role points to that role.
        self.assertIn("limits on role: brightway-analyst-2016", lines["brightway-analyst-2016-EXP-001"])
        # A record's own scope notes appear as a limits note.
        self.assertIn("limits:", lines["NW-EXP-002"])
        # Dictionary date windows and start/end fields print as readable months.
        self.assertIn("Mar 2019 - Jun 2024", lines["NW-ROLE-003"])
        self.assertIn("Mar 2018 - Present", lines["NW-ROLE-001"])
        self.assertNotIn("{", index)

    def test_new_qualification_field_cannot_disappear_from_index(self):
        record = {"id": "new-record", "record_type": "experience", "current_account": "Work summary.",
                  "new_qualification": "Unreleased"}
        with patch.object(current_view, "COLLECTIONS", ["career/x.md"]), \
                patch.object(current_view, "records", return_value=iter([record])), \
                patch.object(sys, "argv", ["current_view.py", "--index"]):
            with self.assertRaisesRegex(SystemExit, "unclassified field.*new_qualification"):
                current_view.main()


class SampleRecordTests(unittest.TestCase):
    def test_sample_record_validates(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
