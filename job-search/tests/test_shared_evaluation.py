import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT.parent / "tools"))
import pipeline as P
import jd_ingest as J
import evaluation as E
import jd_key


class SharedWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        self.text = "Requirements\nLead delivery.\nPython preferred.\nResponsibilities\nLead delivery.\nNew York location.\nBenefits.\n"
        art, normalized = J.ingest(self.text, "user_paste", {}, completeness="complete")
        self.ad = self.d / "artifacts" / art["artifact_id"]
        J.write_artifact(self.ad, art, normalized)
        self.mapping = "skip L1 heading\nWant-1 L2 = Lead delivery.\nNice-1 L3 = Python preferred.\nskip L4 heading\nDo-1 L5 = Lead delivery.\nCond-1 L6 = New York location.\nskip L7 benefits\n"
        code, _, errors, stderr = J.render(self.ad, self.mapping)
        self.assertEqual(code, 0, str(errors) + stderr)
        self.art, _, errors = J.validate_dir(self.ad); self.assertEqual(errors, [])
        self.base = {"id": "hiringcafe:shared", "provider_job_id": "shared", "provider": "hiringcafe", "company": "Example", "title": "PM", "posting_url": "https://example.org/job", "location": "New York, NY", "workplace": "Hybrid", "compensation": "$120,000/yr", "posted_date": "2026-11-10", "jd_artifact": {"artifact_id": art["artifact_id"], "canonical_sha256": art["canonical"]["sha256"]}}
        self.draft = {"id": self.base["id"], "requirements": [self.req("delivery", ["Want-1", "Do-1"], 3), self.req("python", ["Nice-1"], 0, "nice"), self.req("location", ["Cond-1"], None, "condition")], "coverage": {"map_sha256": self.art["selections"]["map_sha256"]}, "adjustment": 3, "adjustment_reason": "Outcome specificity is limited; transferable delivery remains supported.", "card": {"business": "Makes products.", "owns": "Delivery.", "responsibilities": ["Lead delivery."]}, "application_confidence": "medium", "confidence_reason": "Transferable delivery", "strongest_evidence": "Product leadership"}

    def tearDown(self): self.tmp.cleanup()

    def req(self, cid, tags, score, kind="want"):
        item = next(x for x in self.art["selections"]["items"] if x["tag"] == tags[0])
        a, b = item["source"]; quote = self.text[a:b]
        r = {"tag": tags[0], "competency_id": cid, "quote": quote, "kind": kind, "source_tags": tags, "score": score, "record_ids": ["NW-EXP-001"] if score else [], "mandatory": kind == "want", "evidence_note": "Recorded product work" if score else "Not established", "evidence_alignment": "transferable" if score else "none", "result_quality": "unclear" if score else "none", "quote_status": "source_verified", "source": {"tag": tags[0], "source": [a,b], "quote_sha256": hashlib.sha256(quote.encode()).hexdigest()}}
        if r["mandatory"]: r.update(mandatory_basis="explicit", qualification_status="supported")
        if kind == "condition": r["condition_status"] = "pass"
        return r

    def result(self, draft=None): return P.build_result(draft or self.draft, self.base, E.POLICY)

    def test_stage1_search_same_grouping_scores_and_adjustment(self):
        scores = {"Want-1":3,"Do-1":3,"Nice-1":0,"Cond-1":"pass"}
        groups = {"delivery":["Want-1","Do-1"],"python":["Nice-1"]}
        stage = E.assess(E.from_tags(scores, groups=groups), 3, self.draft["adjustment_reason"])
        search = self.result()
        for key in ("evaluation_policy", "baseline_fit", "adjustment", "adjustment_reason", "functional_fit"):
            self.assertEqual(search[key], stage[key])
        self.assertEqual(search["functional_fit"], 53)  # shared-2: (0.75 + 0 x 0.5) / 1.5 = 50, +3 adjustment
        self.assertEqual(search["label"], E.DEPRIORITIZE)  # 53 is below the Stretch band
        self.assertEqual(P.check_job(search, "2026-11-16", P.career_ids(), self.d / "artifacts"), [])

    def test_missing_or_duplicate_mapping_fails(self):
        for mode in ("missing", "duplicate", "stale"):
            job = self.result()
            if mode == "missing": job["requirements"] = job["requirements"][:-1]
            if mode == "duplicate": job["requirements"][1]["source_tags"].append("Do-1")
            if mode == "stale": job["coverage"]["map_sha256"] = "0" * 64
            self.assertTrue(P.check_coverage(job, self.d / "artifacts"))

    def test_kind_must_match_source_tags_as_in_stage1(self):
        fresh = lambda: self.result(copy.deepcopy(self.draft))
        # A nice-to-have scored as a requirement would weigh 1 in search but 0.5 in Stage 1.
        job = fresh(); job["requirements"][1]["kind"] = "want"
        self.assertTrue(any("does not match source tags" in e for e in P.check_coverage(job, self.d / "artifacts")))
        job = fresh(); job["requirements"][0]["kind"] = "do"  # Want-1 + Do-1 merge weighs as want
        self.assertTrue(any("does not match source tags" in e for e in P.check_coverage(job, self.d / "artifacts")))
        job = fresh(); job["requirements"][1]["kind"] = "trait"  # trait is the one allowed override
        self.assertFalse(any("does not match" in e for e in P.check_coverage(job, self.d / "artifacts")))
        self.assertEqual(P.check_coverage(fresh(), self.d / "artifacts"), [])

    def test_coverage_cannot_defer_a_scored_ask(self):
        job = self.result(); job["coverage"]["deferred"] = {"Nice-1": "Not checked"}
        self.assertTrue(P.check_coverage(job, self.d / "artifacts"))

    def test_uncovered_source_text_fails_guard_even_if_artifact_map_is_changed(self):
        art = copy.deepcopy(self.art)
        # check_map alone allows an untouched whole block; render must reject its omission.
        lines = [x for x in self.mapping.splitlines() if not x.startswith("Nice-1")]
        selections, errors = J.check_map(art, (self.ad / "jd.txt").read_text(), lines)
        self.assertEqual(errors, [])
        art["selections"] = J.selections_record(lines, selections)
        (self.ad / "artifact.json").write_text(J.dump_json(art))
        job = self.result(); job["coverage"]["map_sha256"] = art["selections"]["map_sha256"]
        self.assertTrue(P.check_coverage(job, self.d / "artifacts"))

    def test_adjustment_does_not_change_eligibility_or_knockout(self):
        draft = copy.deepcopy(self.draft)
        draft["requirements"][0].update(score=1, qualification_status="unresolved", evidence_alignment="adjacent")
        flagged = self.result(draft)
        self.assertEqual(flagged["eligibility"], "unresolved")
        draft["requirements"][0]["defining"] = True
        # shared-2: a knockout with every ask rated keeps its fit, but no adjustment rescues it.
        stopped = self.result(draft)
        self.assertEqual(stopped["status"], "deprioritized")
        self.assertEqual(stopped["label"], E.DEPRIORITIZE)
        self.assertIsNotNone(stopped["functional_fit"])
        # With asks deferred at the screen, there is no fit to adjust.
        draft["coverage"]["deferred"] = {"Nice-1": "stopped at the knockout screen"}
        draft["requirements"] = [r for r in draft["requirements"] if r["source_tags"] != ["Nice-1"]]
        with self.assertRaises(ValueError): self.result(draft)
        draft["adjustment"] = 0
        deferred = self.result(draft)
        self.assertEqual(deferred["status"], "deprioritized")
        self.assertIsNone(deferred["functional_fit"])
        self.assertEqual(deferred["label"], E.DEPRIORITIZE)

    def test_cli_shared_manifest_full_result_and_status(self):
        doc = {"jobs": [self.base]}
        (self.d / "jobs.json").write_text(json.dumps(doc))
        rules = {"conditions": {"metro_places": ["new york"]}, "max_age_days":30,"min_pay":100000}
        manifest = P.freeze(doc,"shared","2026-11-16","a"*40,True,rules)
        manifest["evaluation_policy"] = E.POLICY
        (self.d / "manifest.json").write_text(json.dumps(manifest))
        (self.d / "draft.json").write_text(json.dumps(self.draft))
        result = subprocess.run([sys.executable,str(ROOT / "tools/pipeline.py"),"result",str(self.d / "draft.json"),"--run-dir",str(self.d)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(P.status(self.d,P.career_ids())["status"],"complete")

    def test_posting_condition_failure_excludes_like_stage1(self):
        # Location metadata passes L1, but the posting text states a conflicting condition.
        draft = copy.deepcopy(self.draft)
        draft["requirements"][2]["condition_status"] = "fail"
        draft["requirements"][2]["evidence_note"] = "Posting requires work in a location outside the metro."
        job = self.result(draft)
        self.assertEqual(job["status"], "excluded")
        self.assertEqual(job["exclusion"]["requirement_quote"], draft["requirements"][2]["quote"])
        self.assertIsNone(job["functional_fit"])
        manifest = {"run_date": "2026-11-16", "l1_rules": {"conditions": P.load_yaml(sample_env.CRITERIA)["conditions"],
                                                           "max_age_days": 30, "min_pay": 100000}}
        job["l1"] = P.l1_check(self.base, manifest["l1_rules"], "2026-11-16", self.d / "artifacts")
        self.assertEqual(job["l1"]["l1"], "pass")
        self.assertEqual(P.enforce_l1(job, self.base, manifest, self.d / "artifacts"), [])
        unsupported = copy.deepcopy(job); unsupported["requirements"][2]["condition_status"] = "pass"
        self.assertTrue(P.enforce_l1(unsupported, self.base, manifest, self.d / "artifacts"))
        unverified = copy.deepcopy(draft); unverified["requirements"][2]["quote_status"] = "unverified"
        with self.assertRaises(ValueError): self.result(unverified)

    def test_label_requirements_met_and_stale(self):
        draft = copy.deepcopy(self.draft); draft["requirements"][0]["score"] = 4; draft["adjustment"] = 0
        draft["requirements"][0]["result_quality"] = "established"
        fresh = P.build_result(draft, self.base, E.POLICY, "2026-11-16", 21)
        self.assertEqual((fresh["functional_fit"], fresh["label"], fresh["requirements_met"], fresh["stale_posting"]),
                         (67, E.STRETCH, {"met": 1, "total": 1}, False))
        old = dict(self.base, posted_date="2026-10-20")
        stale = P.build_result(draft, old, E.POLICY, "2026-11-16", 21)
        self.assertEqual((stale["label"], stale["stale_posting"]), (E.DEPRIORITIZE, True))
        run = {"run_date": "2026-11-16", "l1_rules": {"stale_after_days": 21}}
        self.assertEqual(P.check_label(fresh, "job", run), [])
        tampered = dict(fresh, label=E.PROMISING)
        self.assertTrue(P.check_label(tampered, "job", run))

    def test_mandatory_must_match_want_tags(self):
        job = self.result(copy.deepcopy(self.draft))
        job["requirements"][1]["mandatory"] = True  # a Nice tag claimed as required
        self.assertTrue(any("mandatory must match" in e for e in P.check_label(job, "job", {})))

    def test_review_hides_deprioritize_labels(self):
        promising = dict(self.result(copy.deepcopy(self.draft)), id="a", label=E.PROMISING, status="needs_verification")
        low = dict(promising, id="b", label=E.DEPRIORITIZE, status="eligible")
        run = {"jobs": [low, promising], "discovered_count": 2}
        self.assertEqual([j["id"] for j in P.review_queue(run)], ["a"])
        self.assertEqual([j["id"] for j in P.review_queue(run, include_all=True)], ["a", "b"])


if __name__ == "__main__": unittest.main()
