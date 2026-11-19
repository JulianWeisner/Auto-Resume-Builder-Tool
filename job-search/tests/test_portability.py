"""Cross-host intake, candidate dedup, completion and enforced L1 regressions."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hiringcafe as H
import intake as I
import pipeline as P


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Formats(unittest.TestCase):
    def setUp(self):
        self.structured = json.loads((ROOT / "tests/fixtures/search-structured.json").read_text())
        self.markdown = (ROOT / "tests/fixtures/search-markdown.md").read_text()

    def test_both_formats_and_json_envelope(self):
        for value in [self.structured, json.dumps(self.structured), self.markdown,
                      {"content": [{"type": "text", "text": self.markdown}]}]:
            self.assertEqual(H.parse_search(value)[0]["job_id"], "example")

    def test_unknown_format_never_means_zero(self):
        for value in ["Found 10 jobs", {"surprise": []}, {"isError": True, "jobs": []},
                      {"jobs": [], "count": 10}, {"jobs": [{"id": "broken"}], "count": 1}]:
            with self.assertRaises(I.IntakeError):
                H.parse_search(value)

    def test_explicit_empty_is_valid(self):
        self.assertEqual(H.parse_search({"jobs": [], "count": 0}), [])
        self.assertEqual(H.parse_search("## HiringCafe job results (showing 0 of 0 matches)"), [])

    def test_bad_encoding_is_contained_and_original_bytes_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp); source = d / "searches"; source.mkdir()
            write(source / "a.json", self.structured)
            (source / "b.md").write_bytes(b"\xff\xfe")
            write(d / "plan.json", {"searches": [{"id": "a", "text": "PM"}, {"id": "b", "text": "Chef"}]})
            result = H.write_search_log(source, d)
            self.assertEqual((result["searches_logged"], result["unresolved"]), (1, 1))
            self.assertIn(b"\xff\xfe", [p.read_bytes() for p in (d / "raw/searches").iterdir()])

    def test_unreadable_page_does_not_erase_other_searches(self):
        plan = {"searches": [{"id": "a", "text": "product manager"}, {"id": "b", "text": "chef"}]}
        log = H.search_log([({"plan_id": "a"}, self.structured), ({"plan_id": "b"}, "changed format")], plan)
        self.assertEqual([e["status"] for e in log["searches"]], ["run", "unresolved"])
        self.assertEqual(log["searches"][0]["results"], 1)
        # A bad additional page must not become a successful empty page.
        log = H.search_log([({"plan_id": "a"}, self.structured), ({"plan_id": "a"}, "bad page")], plan)
        self.assertEqual(log["searches"][0]["status"], "unresolved")

    def test_files_keep_originals_and_requested_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp); (d / "responses").mkdir()
            payload = {"plan_id": "a", "request": {"prompt": "Product manager in New York"}, "response": self.structured}
            write(d / "responses/a.json", payload)
            write(d / "plan.json", {"searches": [{"id": "a", "text": "product manager", "requested_filters": {"location": "New York, NY", "posted_within_days": 30}}]})
            H.write_search_log(d / "responses", d)
            receipt = json.loads((d / "search_log.json").read_text())["searches"][0]["receipts"][0]
            self.assertEqual(receipt["request"]["prompt"], payload["request"]["prompt"])
            self.assertEqual([c["status"] for c in receipt["filter_checks"]], ["changed", "unknown"])
            self.assertEqual(next((d / "raw/searches").glob("*.response")).read_bytes(), (d / "responses/a.json").read_bytes())

    def test_detail_structured_and_original_error_preservation(self):
        value = {"job": {"id": "a", "title": "Product Manager", "company": "Example", "applyUrl": "https://hiringcafe.com/job/a",
                         "description": "Own the roadmap.", "compensation": {"currency": "USD", "frequency": "Yearly", "minimum": 90000, "maximum": 120000}}}
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            result = H.process([("a", json.dumps(value), None), ("bad", "format changed", None)], d)
            self.assertEqual((result["unique"], len(result["problems"])), (1, 1))
            self.assertEqual(len(list((d / "raw/hiringcafe").glob("*.original"))), 2)
            self.assertEqual(json.loads((d / "jobs.json").read_text())["jobs"][0]["compensation"], "$90,000 – $120,000/yr")

    def test_conflicting_repeated_details_stay_unresolved(self):
        row = {"id": "a", "title": "PM", "company": "Example", "applyUrl": "https://hiringcafe.com/job/a", "description": "Original description."}
        newer = dict(row, description="Different description.")
        with tempfile.TemporaryDirectory() as tmp:
            result = H.process([("a", {"job": row}, None), ("a", {"job": newer}, None)], tmp)
            self.assertEqual(result["unique"], 1)
            self.assertIn("conflicting", result["problems"][0])


class CandidateRegressions(unittest.TestCase):
    def setUp(self):
        self.plan = {"target_unique_jobs": 2, "searches": [
            {"id": "hardware", "family": "hardware", "tier": "core", "text": "hardware product manager"},
            {"id": "culinary", "family": "culinary", "tier": "core", "text": "research chef"}]}
        self.criteria = {"search": {"max_posting_age_days": 30, "role_families": [
            {"id": "hardware", "titles": ["hardware product manager"]},
            {"id": "culinary", "titles": ["research chef"]}], "title_stopwords": ["manager"]}}

    def select(self, a, b):
        return P.candidates(self.plan, {"searches": [{"id": "hardware", "status": "run", "items": a},
                                                   {"id": "culinary", "status": "run", "items": b}]}, self.criteria, "2026-11-16")

    def item(self, jid="a", **kw):
        return dict({"job_id": jid, "company": "Example", "title": "Research Chef", "posted_date": "2026-11-10"}, **kw)

    def test_mismatched_family_does_not_poison_later_match(self):
        self.assertEqual(self.select([self.item()], [self.item()])["selected"], ["a"])

    def test_old_occurrence_does_not_hide_fresh_repost(self):
        r = self.select([self.item("old", posted_date="2026-09-01")], [self.item("fresh")])
        self.assertEqual(r["selected"], ["fresh"])

    def test_distinct_locations_and_missing_location_keep_distinct_ids(self):
        for locs in [("New York", "Boston"), (None, None)]:
            r = self.select([], [self.item("a", location=locs[0]), self.item("b", location=locs[1])])
            self.assertEqual(r["selected"], ["a", "b"])

    def test_reordered_location_lists_merge(self):
        r = self.select([], [self.item("a", location="New York or Boston"), self.item("b", location="Boston or New York")])
        self.assertEqual(r["selected"], ["a"])

    def test_zero_candidates_cannot_complete_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            write(d / "manifest.json", P.freeze({"jobs": []}, "t", "2026-11-16", "a" * 40))
            write(d / "plan.json", {"target_unique_jobs": 30, "searches": []})
            write(d / "candidates.json", {"selected": []})
            result = P.status(d)
            self.assertEqual(result["status"], "partial")
            self.assertTrue(any("0 of 30" in x for x in result["problems"]))


class EnforcedScreen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.tmp.name)
        text = ("# [Product Manager](https://hiringcafe.com/job/a)\n**Example**\n\n"
                "- **Location:** New York, NY\n- **Workplace:** Hybrid\n- **Posted:** 2026-11-10\n- **Job ID:** a\n"
                "- **Compensation:** $110,000 – $130,000/yr\n\n## Full description\nOwn the roadmap.\n"
                "Example makes kitchen tools for home cooks. The product manager works with engineering, design and "
                "operations to plan releases and report results to leadership.\n")
        H.process([("a", text, None)], self.d)
        self.doc = json.loads((self.d / "jobs.json").read_text()); self.base = self.doc["jobs"][0]
        self.rules = {"conditions": {"metro_places": ["new york"]}, "max_age_days": 30, "min_pay": 100000}

    def tearDown(self):
        self.tmp.cleanup()

    def draft(self):
        from test_funnel import ask
        return {"id": self.base["id"], "requirements": [ask("product", 3, quote="Own the roadmap.", mandatory_basis="explicit")],
                "card": {"business": "Makes products.", "owns": "The roadmap.", "responsibilities": ["Own the roadmap."]},
                "application_confidence": "medium", "confidence_reason": "Product experience", "strongest_evidence": "Product work"}

    def manifest(self):
        m = P.freeze(self.doc, "t", "2026-11-16", "a" * 40, frozen_input=True, l1_rules=self.rules)
        write(self.d / "manifest.json", m); return m

    def test_result_cli_enforces_old_posting_before_writing(self):
        self.base["posted_date"] = "2026-01-01"; write(self.d / "jobs.json", self.doc); self.manifest()
        write(self.d / "draft.json", self.draft())
        r = subprocess.run([sys.executable, str(ROOT / "tools/pipeline.py"), "result", str(self.d / "draft.json"), "--run-dir", str(self.d)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(next((self.d / "results").glob("*.json")).read_text())
        self.assertEqual(result["status"], "evaluation_error"); self.assertIsNone(result["fit_percent"])
        self.assertEqual(P.status(self.d)["status"], "complete")

    def test_stale_receipt_and_changed_inputs_fail(self):
        m = self.manifest(); job = P.build_result(self.draft(), self.base)
        job["l1"] = P.l1_check(self.base, self.rules, m["run_date"], self.d / "artifacts")
        write(self.d / m["jobs"][0]["result_file"], job)
        self.assertEqual(P.status(self.d)["status"], "complete")
        self.base["compensation"] = "$50,000/yr"; write(self.d / "jobs.json", self.doc)
        self.assertEqual(P.status(self.d)["status"], "failed")
        job["posted_date"] = "2026-01-01"
        self.assertTrue(P.enforce_l1(job, job, m, self.d / "artifacts"))

    def test_pay_floor_and_unknown_travel_enforced(self):
        self.base["compensation"] = "$60,000/yr"
        self.assertEqual(P.l1_check(self.base, self.rules, "2026-11-16", self.d / "artifacts")["l1"], "fail")
        self.base["compensation"] = "$120,000/yr"; self.base["travel_percent"] = 75
        self.assertEqual(P.l1_check(self.base, self.rules, "2026-11-16", self.d / "artifacts")["l1"], "unknown")
        m = self.manifest(); job = P.build_result(self.draft(), self.base)
        job["l1"] = P.l1_check(self.base, self.rules, "2026-11-16", self.d / "artifacts")
        self.assertTrue(any("cannot be eligible" in e for e in P.enforce_l1(job, self.base, m, self.d / "artifacts")))

    def test_missing_location_is_unknown_and_us_remote_alternative_is_allowed(self):
        self.base["location"] = None
        self.assertEqual(P.l1_check(self.base, self.rules, "2026-11-16", self.d / "artifacts")["l1"], "unknown")
        self.base.update(location="United States or Canada", workplace="Remote")
        self.rules["conditions"]["remote_excluded_regions"] = ["canada"]
        self.assertEqual(P.l1_check(self.base, self.rules, "2026-11-16", self.d / "artifacts")["l1"], "pass")

    def test_cli_rejects_inferred_mandatory_draft_without_writing(self):
        self.manifest(); draft = self.draft(); draft["requirements"][0]["mandatory_basis"] = "inferred"
        write(self.d / "draft.json", draft)
        result = subprocess.run([sys.executable, str(ROOT / "tools/pipeline.py"), "result", str(self.d / "draft.json"), "--run-dir", str(self.d)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list((self.d / "results").glob("*.json")))

    def test_inferred_responsibility_cannot_be_a_mandatory_knockout(self):
        m = self.manifest(); d = self.draft(); d["requirements"][0].update(mandatory_basis="inferred", kind="do")
        j = P.build_result(d, self.base); j["l1"] = P.l1_check(self.base, self.rules, m["run_date"], self.d / "artifacts")
        write(self.d / m["jobs"][0]["result_file"], j)
        self.assertEqual(P.status(self.d)["status"], "failed")

    def test_choice_file_identity_and_import(self):
        run = {"run_id": "t", "run_date": "2026-11-16", "source_commit": "a" * 40,
               "jobs": [{"id": "a", "decision": "undecided"}]}
        file = {"kind": "decisions", "run_id": "t", "source_commit": "a" * 40,
                "selection_key": P.selection_key(run), "decisions": {"a": "interested"}}
        self.assertEqual(P.apply_decisions(run, file)["interested"], 1)
        file["selection_key"] = "different"
        with self.assertRaises(ValueError): P.apply_decisions(run, file)
        # Original portable files remain supported.
        P.apply_decisions(run, {"run_id": "t", "decisions": {"a": "pass"}})


if __name__ == "__main__":
    unittest.main()
