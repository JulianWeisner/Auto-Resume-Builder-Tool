"""Layered funnel (schema 1.3): shared fit, L2 routing, decision rules, review order, L1 screen,
capability profile and the Greenhouse source."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import jd_ingest  # noqa: E402
import pipeline as P  # noqa: E402

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover
    yaml = None


def ask(cid, score, kind="want", mandatory=True, **kw):
    r = {"tag": cid, "quote": f"quote {cid}", "kind": kind, "score": score, "record_ids": ["NW-EXP-001"] if score else [],
         "competency_id": cid, "mandatory": mandatory, "evidence_note": "note",
         "evidence_alignment": "none" if score == 0 else "direct" if score >= 3 else "adjacent",
         "result_quality": "established" if score == 4 else "unclear" if score else "none"}
    if mandatory:
        r["qualification_status"] = "supported" if score >= 3 else "unresolved"
    r.update(kw)
    return r


def job(jid, reqs, status=None, eligibility=None, confidence="medium", fit=True):
    route = P.routing(reqs)
    gaps = P.critical_gaps(reqs)
    mand = [r for r in reqs if r.get("mandatory")]
    elig = eligibility or ("pass" if all(r["qualification_status"] == "supported" for r in mand) else "unresolved")
    st = status or ("deprioritized" if route == "deprioritized" else "eligible" if elig == "pass" else "needs_verification")
    f = P.fit(reqs) if fit else None
    return {"id": jid, "provider": "test", "company": jid, "title": "PM", "posting_url": "https://example.org",
            "status": st, "decision": "undecided", "fit_percent": f, "functional_fit": f, "eligibility": elig,
            "application_confidence": confidence, "confidence_reason": "reason", "requirements": reqs, "exclusion": None,
            "screen": {"critical_gaps": gaps, "routing": route, "reason": "two hard gaps" if route == "deprioritized" else None},
            "posted_date": "2026-11-01", "card": {"business": "Sells things.", "owns": "The roadmap.", "responsibilities": ["Own it."]},
            "strongest_evidence": "Owned a consumer app."}


def run_of(*jobs):
    return {"schema_version": "1.3", "run_id": "t", "run_date": "2026-11-16", "source_commit": "0" * 40, "search_criteria": "x",
            "discovered_count": len(jobs), "duplicate_count": 0, "jobs": list(jobs)}


class FitAndRouting(unittest.TestCase):
    def test_fit_uses_shared_engine(self):
        reqs = [ask("a", 4), ask("b", 3), ask("c", 2, kind="trait", mandatory=False)]
        self.assertEqual(P.fit(reqs), round((1 + 0.75 + 0.5 * 0.5) / 2.5 * 100))
        self.assertIsNone(P.fit([dict(ask("a", 2), score=None)]))
        self.assertIsNone(P.fit([]))

    def test_routing_branches(self):
        self.assertEqual(P.routing([ask("a", 4), ask("b", 3)]), "full_score")
        self.assertEqual(P.routing([ask("a", 1), ask("b", 3)]), "full_score_flagged")
        self.assertEqual(P.routing([ask("a", 1), ask("b", 0)]), "deprioritized")
        self.assertEqual(P.routing([ask("a", 1, defining=True), ask("b", 4)]), "deprioritized")
        self.assertEqual(P.routing([ask("a", 2, qualification_status="unmet", contradiction="May 2018 start"),
                                    ask("b", 1)]), "deprioritized")
        self.assertEqual(P.routing([ask("a", 0, mandatory=False, kind="nice"), ask("b", 4)]), "full_score")


class Validation(unittest.TestCase):
    def setUp(self):
        self.good = run_of(job("j1", [ask("a", 4), ask("b", 3)]),
                           job("j2", [ask("c", 1), ask("d", 3)]),
                           job("j3", [ask("e", 1), ask("f", 0)], fit=False))

    def errs(self, run):
        return P.validate(run)

    def test_valid_run(self):
        self.assertEqual(self.errs(self.good), [])
        self.assertEqual([j["status"] for j in self.good["jobs"]], ["eligible", "needs_verification", "deprioritized"])

    def test_screen_required_and_recomputed(self):
        r = copy.deepcopy(self.good); r["jobs"][0].pop("screen")
        self.assertTrue(any("screen object" in e for e in self.errs(r)))
        r = copy.deepcopy(self.good); r["jobs"][1]["screen"]["routing"] = "full_score"
        self.assertTrue(any("screen.routing" in e for e in self.errs(r)))
        r = copy.deepcopy(self.good); r["jobs"][1]["screen"]["critical_gaps"] = []
        self.assertTrue(any("critical_gaps" in e for e in self.errs(r)))
        r = copy.deepcopy(self.good); r["jobs"][2]["status"] = "needs_verification"
        self.assertTrue(any("deprioritized exactly" in e for e in self.errs(r)))
        r = copy.deepcopy(self.good); r["jobs"][2]["screen"]["reason"] = ""
        self.assertTrue(any("one-line" in e for e in self.errs(r)))

    def test_deprioritized_fit_null_or_exact(self):
        r = copy.deepcopy(self.good)
        f = P.fit(r["jobs"][2]["requirements"])
        r["jobs"][2]["fit_percent"] = r["jobs"][2]["functional_fit"] = f
        self.assertEqual(self.errs(r), [])
        r["jobs"][2]["fit_percent"] = f + 1
        self.assertTrue(any("computed" in e for e in self.errs(r)))

    def test_decision_rules(self):
        cases = [
            (ask("a", 2, qualification_status="supported"), "supported needs a score of 3"),
            (ask("a", 3, qualification_status="unresolved"), "threshold_note"),
            (ask("a", 2, qualification_status="unmet"), "contradiction"),
            (ask("a", 4, kind="nice", mandatory=False, defining=True), "defining ask must be mandatory"),
        ]
        for bad, msg in cases:
            r = run_of(job("j", [bad, ask("z", 4)], status="needs_verification", eligibility="unresolved"))
            self.assertTrue(any(msg in e for e in self.errs(r)), msg)
        ok = run_of(job("j", [ask("a", 3, qualification_status="unresolved", threshold_note="9.6 of 10 years"),
                              ask("z", 4)], eligibility="unresolved"))
        self.assertEqual(self.errs(ok), [])

    def test_only_current_schema(self):
        for old in ("1.0", "1.1", "1.2"):
            r = copy.deepcopy(self.good); r["schema_version"] = old
            self.assertTrue(any("schema_version must be 1.3" in e for e in self.errs(r)))

    def test_review_order_and_summary(self):
        a = job("pass-low", [ask("a", 3), ask("b", 3)], confidence="low")
        b = job("pass-high", [ask("a", 3), ask("b", 4)], confidence="high")
        c = job("flag", [ask("a", 1), ask("b", 4)], confidence="high")
        d = job("drop", [ask("a", 0), ask("b", 0)], confidence="high", fit=False)
        r = run_of(c, a, d, b)
        self.assertEqual(P.validate(r), [])
        self.assertEqual([j["id"] for j in P.review_queue(r)], ["pass-high", "pass-low", "flag"])
        self.assertEqual([j["id"] for j in P.review_queue(r, True)][-1], "drop")
        s = P.summary(r)
        self.assertEqual((s["deprioritized"], s["eligible"], s["review_queue"]), (1, 2, 3))


@unittest.skipUnless(yaml, "PyYAML needed for screen and profile")
class ScreenAndProfile(unittest.TestCase):
    def setUp(self):
        self.profile = P.load_yaml(sample_env.PROFILE)
        self.cond = P.load_yaml(sample_env.CRITERIA)["conditions"]

    def test_screen_conditions(self):
        cases = {("Miami or New York City", "Onsite"): "pass", ("Miami, Florida", "Onsite"): "fail",
                 ("United States", "Remote"): "pass", ("Dublin, Ireland", "Remote"): "unknown",
                 ("Dayton, New Jersey, United States", "Hybrid"): "pass", ("", ""): "unknown"}
        for (loc, wp), want in cases.items():
            self.assertEqual(P.screen_job({"location": loc, "workplace": wp}, self.cond)[0], want, loc)
        res = P.screen_job({"location": "New York", "workplace": "Hybrid", "travel_percent": 70}, self.cond)
        self.assertEqual(res[0], "unknown")

    def test_screen_truncated_artifact(self):
        text = "Role text\n\n…(truncated — read the full posting at https://hiringcafe.com/job/x)"
        art, norm = jd_ingest.ingest(text, "hiringcafe", {"provider_job_id": "x"})
        with tempfile.TemporaryDirectory() as tmp:
            jd_ingest.write_artifact(Path(tmp) / art["artifact_id"], art, norm)
            j = {"location": "New York", "workplace": "Hybrid", "jd_artifact": {"artifact_id": art["artifact_id"]}}
            self.assertEqual(P.screen_job(j, self.cond, tmp)[0], "evaluation_error")

    def test_profile_checks(self):
        errors, _ = P.check_profile(self.profile)
        self.assertEqual(errors, [])
        bad = copy.deepcopy(self.profile)
        bad["strengths"][0]["record_ids"] = ["NOT-A-RECORD"]
        bad["strengths"].append(dict(bad["strengths"][1]))
        errors, _ = P.check_profile(bad)
        self.assertTrue(any("unknown record" in e for e in errors))
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_profile_rejects_no_entries(self):
        bad = copy.deepcopy(self.profile)
        bad["strengths"].append({"id": "marketplace", "label": "x", "score": 0, "record_ids": []})
        bad["partials"][0]["score"] = 3
        bad["competencies"] = []
        errors, _ = P.check_profile(bad)
        self.assertTrue(any("marketplace" in e and "limits on a strength" in e for e in errors))
        self.assertTrue(any("marketplace" in e and "record_id" in e for e in errors))
        self.assertTrue(any("partials entries" in e for e in errors))
        self.assertTrue(any("no 'no' entries" in e for e in errors))


class GreenhouseSource(unittest.TestCase):
    RAW = json.dumps({"title": "PM", "content": "&lt;p&gt;&lt;strong&gt;About&lt;/strong&gt; us&amp;nbsp;now&lt;/p&gt;"
                      "&lt;ul&gt;&lt;li&gt;Ship &amp;amp; learn&lt;/li&gt;&lt;li&gt;Lead&lt;br&gt;teams&lt;/li&gt;&lt;/ul&gt;"}).encode()

    def test_text_derivation(self):
        text = jd_ingest.greenhouse_text(self.RAW)
        self.assertEqual(text, "About us now\n• Ship & learn\n• Lead\nteams\n")
        self.assertEqual(text, jd_ingest.greenhouse_text(self.RAW))

    def test_ingest_requires_response_hash(self):
        text = jd_ingest.greenhouse_text(self.RAW)
        with self.assertRaises(jd_ingest.IngestError):
            jd_ingest.ingest(text, "greenhouse", {"board": "b", "provider_job_id": "1"})
        art, _ = jd_ingest.ingest(text, "greenhouse", {"board": "b", "provider_job_id": "1",
                                                      "response_sha256": hashlib.sha256(self.RAW).hexdigest()})
        self.assertEqual(art["source"]["text_derivation"], "gh-text-1")
        # A ten-word provider description is a stub, not a posting.
        self.assertEqual(art["source"]["completeness"], {"status": "insufficient", "basis": "too_few_words", "words": 10})


if __name__ == "__main__":
    unittest.main()
