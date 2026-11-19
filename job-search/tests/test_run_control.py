"""Run control: plan, freeze, per-job results and the status code decides; plus the frozen regression set."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hiringcafe  # noqa: E402
import pipeline as P  # noqa: E402

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover
    yaml = None

FIXTURE = json.loads((ROOT / "tests/fixtures/sample_run.json").read_text())
REG = ROOT / "tests/regression"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


class RunControl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        jobs = copy.deepcopy(FIXTURE["jobs"])
        for j in jobs:
            j["jd_artifact"] = {"artifact_id": "a-" + j["provider_job_id"], "canonical_sha256": "f" * 64}
        self.jobs = jobs
        doc = {"discovered": 6, "duplicates": 1, "jobs": jobs}
        self.manifest = P.freeze(doc, "t", "2026-11-16", "0" * 40)
        write(self.dir / "manifest.json", self.manifest)
        self.plan = {"target_unique_jobs": 5, "searches": [{"id": "a:1"}, {"id": "a:remote"}]}
        write(self.dir / "plan.json", self.plan)
        write(self.dir / "search_log.json", {"searches": [{"id": "a:1", "status": "run", "results": 10},
                                                          {"id": "a:remote", "status": "run", "results": 3}]})
        for j, e in zip(jobs, self.manifest["jobs"]):
            write(self.dir / e["result_file"], j)

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete(self):
        r = P.status(self.dir, P.career_ids())
        self.assertEqual(r["status"], "complete", r["problems"])
        run = P.assemble(self.dir)
        self.assertEqual(P.validate(run), [])

    def test_missing_result_is_partial(self):
        (self.dir / self.manifest["jobs"][1]["result_file"]).unlink()
        r = P.status(self.dir)
        self.assertEqual(r["status"], "partial")
        self.assertTrue(any("no result" in p for p in r["problems"]))

    def test_skipped_search_is_partial(self):
        write(self.dir / "search_log.json", {"searches": [{"id": "a:1", "status": "run"},
                                                          {"id": "a:remote", "status": "skipped", "reason": "cost"}]})
        r = P.status(self.dir)
        self.assertEqual(r["status"], "partial")
        self.assertTrue(any("a:remote skipped: cost" in p for p in r["problems"]))

    def test_too_few_jobs_is_partial(self):
        self.plan["target_unique_jobs"] = 40
        write(self.dir / "plan.json", self.plan)
        self.assertTrue(any("5 of 40" in p for p in P.status(self.dir)["problems"]))

    def test_wrong_work_is_failed(self):
        bad = copy.deepcopy(self.jobs[0]); bad["fit_percent"] = 99
        write(self.dir / self.manifest["jobs"][0]["result_file"], bad)
        self.assertEqual(P.status(self.dir)["status"], "failed")
        bad = copy.deepcopy(self.jobs[0]); bad["jd_artifact"]["canonical_sha256"] = "0" * 64
        write(self.dir / self.manifest["jobs"][0]["result_file"], bad)
        self.assertTrue(any("posting hash" in p for p in P.status(self.dir)["problems"]))
        write(self.dir / "results/stray.json", self.jobs[0])
        self.assertTrue(any("not in the manifest" in p for p in P.status(self.dir)["problems"]))

    def test_unknown_record_id_fails(self):
        bad = copy.deepcopy(self.jobs[0]); bad["requirements"][0]["record_ids"] = ["NOT-A-RECORD"]
        self.assertTrue(any("does not exist" in e for e in P.check_job(bad, "2026-11-16", P.career_ids())))

    def test_expectations(self):
        exp = {"jobs": {self.jobs[0]["id"]: ["deprioritized"]}}
        r = P.status(self.dir, expect=exp)
        self.assertEqual(r["status"], "failed")

    def test_cards_show_incomplete_run(self):
        run = P.assemble(self.dir)
        run["completion"] = {"status": "partial", "problems": ["search a:remote skipped: cost"]}
        self.assertEqual(P.card_data(run)["completion"]["status"], "partial")

    @unittest.skipUnless(yaml, "PyYAML needed")
    def test_plan_from_criteria(self):
        pl = P.plan(P.load_yaml(sample_env.CRITERIA), target=40)
        ids = [s["id"] for s in pl["searches"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("hardware-product:remote", ids)
        self.assertEqual((pl["target_cards"], pl["first_batch"], pl["fetch_cap"]), (40, 60, 120))
        food = next(s for s in pl["searches"] if s["id"] == "domain:food-beverage-cpg")
        self.assertEqual(food["industries"], ["Food"])


class BuildResult(unittest.TestCase):
    """pipeline.build_result: the agent supplies judgments, code computes everything else."""

    def base(self):
        j = FIXTURE["jobs"][0]
        return {k: j[k] for k in ("id", "provider", "provider_job_id", "company", "title", "posting_url", "location",
                                  "workplace", "compensation", "posted_date", "deadline")}

    def draft(self, **kw):
        j = FIXTURE["jobs"][0]
        d = {"id": j["id"], "requirements": copy.deepcopy(j["requirements"]), "card": j["card"],
             "application_confidence": "high", "confidence_reason": "r", "strongest_evidence": "s"}
        d.update(kw)
        return d

    def test_eligible_matches_fixture(self):
        job = P.build_result(self.draft(), self.base())
        self.assertEqual((job["status"], job["fit_percent"]), ("eligible", FIXTURE["jobs"][0]["fit_percent"]))
        self.assertEqual(P.check_job(job, "2026-11-16", P.career_ids()), [])

    def test_unresolved_and_deprioritized(self):
        d = self.draft()
        d["requirements"][1].update(score=2, qualification_status="unresolved", evidence_alignment="adjacent",
                                    result_quality="unclear")
        self.assertEqual(P.build_result(d, self.base())["status"], "needs_verification")
        d = self.draft(l3=False, screen_reason="Two critical gaps.")
        for r in d["requirements"][:2]:
            r.update(score=0, qualification_status="unresolved", evidence_alignment="none", result_quality="none",
                     record_ids=[])
        d["requirements"][0].pop("defining")
        job = P.build_result(d, self.base())
        self.assertEqual((job["status"], job["fit_percent"], job["card"]), ("deprioritized", None, None))
        self.assertEqual(P.check_job(job, "2026-11-16"), [])

    def test_error_and_excluded(self):
        job = P.build_result({"id": "x", "status": "evaluation_error", "error_reason": "truncated"}, self.base())
        self.assertEqual(P.check_job(job, "2026-11-16"), [])
        ex = FIXTURE["jobs"][3]
        job = P.build_result({"id": ex["id"], "status": "excluded", "requirements": ex["requirements"],
                              "exclusion": ex["exclusion"], "confidence_reason": "pay"}, self.base())
        self.assertEqual(P.check_job(job, "2026-11-16"), [])


class CardQuotes(unittest.TestCase):
    def test_card_responsibility_must_appear_in_posting(self):
        import jd_ingest
        text = "About us\n\nOwn the roadmap from discovery to launch.\nWork daily with hardware and app engineers.\n"
        art, norm = jd_ingest.ingest(text, "hiringcafe", {"provider_job_id": "x"}, completeness="complete")
        with tempfile.TemporaryDirectory() as tmp:
            jd_ingest.write_artifact(Path(tmp) / art["artifact_id"], art, norm)
            run = copy.deepcopy(FIXTURE)
            run["jobs"] = [run["jobs"][0]]
            run["jobs"][0]["requirements"] = []
            run["jobs"][0]["jd_artifact"] = {"artifact_id": art["artifact_id"], "canonical_sha256": art["canonical"]["sha256"]}
            self.assertEqual(P.quote_warnings(run, tmp), [])
            run["jobs"][0]["card"]["responsibilities"] = ["Own the roadmap end to end."]
            self.assertTrue(any("card" in w for w in P.quote_warnings(run, tmp)))


class Export(unittest.TestCase):
    def test_interested_jobs_with_posting_text(self):
        import jd_ingest
        text = "About us\n\nOwn the roadmap from discovery to launch.\n"
        art, norm = jd_ingest.ingest(text, "hiringcafe", {"provider_job_id": "x"}, completeness="complete")
        run = copy.deepcopy(FIXTURE)
        run["jobs"][0]["jd_artifact"] = {"artifact_id": art["artifact_id"], "canonical_sha256": art["canonical"]["sha256"]}
        P.apply_decisions(run, {run["jobs"][0]["id"]: "interested", run["jobs"][1]["id"]: "pass"})
        with tempfile.TemporaryDirectory() as tmp:
            jd_ingest.write_artifact(Path(tmp) / art["artifact_id"], art, norm)
            q = P.export_queue(run, tmp, "2026-11-17")
        self.assertEqual([x["job_id"] for x in q["jobs"]], [run["jobs"][0]["id"]])
        item = q["jobs"][0]
        self.assertEqual((item["decision"], item["application_status"]), ("interested", "not_started"))
        self.assertEqual(item["posting"]["text"], text)
        self.assertEqual(item["screening"]["fit_percent"], run["jobs"][0]["fit_percent"])
        self.assertEqual(q["counts"]["pass"], 1)
        self.assertEqual(q["source"]["completion"], "not checked")

    def test_decisions_file_from_page(self):
        run = copy.deepcopy(FIXTURE)
        jid = run["jobs"][0]["id"]
        counts = P.apply_decisions(run, {"kind": "decisions", "run_id": run["run_id"], "decisions": {jid: "interested"}})
        self.assertEqual(counts["interested"], 1)
        with self.assertRaises(ValueError):
            P.apply_decisions(run, {"kind": "decisions", "run_id": "other-run", "decisions": {jid: "pass"}})


class Candidates(unittest.TestCase):
    @unittest.skipUnless(yaml, "PyYAML needed")
    def test_selection_is_decided_by_code(self):
        crit = P.load_yaml(sample_env.CRITERIA)
        plan = {"target_unique_jobs": 3, "searches": [
            {"id": "culinary-product:1", "family": "culinary-product", "tier": "core", "text": "culinary product manager"},
            {"id": "chief-of-staff:1", "family": "chief-of-staff", "tier": "strong", "text": "chief of staff"}]}
        item = lambda jid, title, company, posted: {"job_id": jid, "title": title, "company": company,
                                                    "posted_date": posted, "url": "u"}
        log = {"searches": [
            {"id": "chief-of-staff:1", "status": "run", "items": [
                item("c1", "Chief of Staff", "A", "2026-11-10"), item("c2", "Senior Manager, Pricing", "B", "2026-11-10")]},
            {"id": "culinary-product:1", "status": "run", "items": [
                item("k1", "Culinary Product Manager", "C", "2026-09-01"),
                item("k2", "Research Chef", "D", "2026-11-12"),
                item("k3", "Culinary Innovation Manager", "E", None),
                item("k4", "Culinary Innovation Manager", "E", "2026-11-12"),
                item("c1", "Chief of Staff", "A", "2026-11-10")]}]}
        r = P.candidates(plan, log, crit, "2026-11-16")
        self.assertEqual(r["selected"], ["k2", "c1", "k3"])  # core first in each round; target 3
        why = {x["job_id"]: x["reason"] for x in r["results"]}
        self.assertEqual(why["k1"], "posted 76 days ago")
        self.assertEqual(why["c2"], "title shares no word with the family")
        self.assertEqual(why["k4"], "not reached (target met)")  # distinct ID, location unknown: do not assume duplicate
        self.assertEqual(r["counts"]["too old"], 1)

    def test_status_requires_the_selected_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            jobs = [{"id": "hiringcafe:k2", "jd_artifact": {}}, {"id": "hiringcafe:zz", "jd_artifact": {}}]
            write(d / "manifest.json", P.freeze({"jobs": jobs}, "t", "2026-11-16", "0" * 40))
            write(d / "plan.json", {"target_unique_jobs": 2, "searches": []})
            write(d / "candidates.json", {"selected": ["k2", "c1"]})
            probs = P.status(d)["problems"]
        self.assertTrue(any("candidate c1 was not fetched" in x for x in probs))
        self.assertTrue(any("hiringcafe:zz is in the manifest but was not a selected candidate" in x for x in probs))


class SearchLog(unittest.TestCase):
    RESULT = ("## HiringCafe job results (showing 2 of 9 matches)\n\n### [PM](https://hiringcafe.com/job/a)\n**A**\n"
              "- **Job ID:** aaa\n\n---\n\n### [PM](https://hiringcafe.com/job/b)\n**B**\n- **Job ID:** bbb\n")

    def test_matches_plan_keeps_skips_and_extras(self):
        plan = {"searches": [{"id": "f:1", "text": "Product Manager"}, {"id": "f:remote", "text": "product manager",
                                                                       "workplace": "Remote"},
                             {"id": "domain:food", "text": "product manager", "industries": ["Food"]},
                             {"id": "f:2", "text": "chief of staff"}]}
        calls = [{"search": "product  manager"}, {"search": "product manager", "workplace_types": ["Remote"]},
                 {"search": "product manager", "industries": ["Food"]}, {"search": "something else"}]
        with tempfile.TemporaryDirectory() as tmp:
            lines = []
            for n, inp in enumerate(calls):
                lines.append({"message": {"content": [{"type": "tool_use", "id": f"s{n}",
                                                       "name": "mcp__x__search_jobs", "input": inp}]}})
                lines.append({"message": {"content": [{"type": "tool_result", "tool_use_id": f"s{n}",
                                                       "content": [{"type": "text", "text": self.RESULT}]}]}})
            path = Path(tmp) / "t.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in lines))
            existing = {"searches": [{"id": "f:2", "status": "skipped", "reason": "tested"}]}
            log = hiringcafe.search_log(hiringcafe.search_responses(path), plan, existing)
        self.assertEqual([e["id"] for e in log["searches"]], ["f:1", "f:remote", "domain:food", "f:2"])
        self.assertEqual([i["job_id"] for i in log["searches"][0]["items"]], ["aaa", "bbb"])
        self.assertEqual(log["searches"][3]["status"], "skipped")
        self.assertEqual(len(log["extra"]), 1)


@unittest.skipUnless(yaml, "PyYAML needed for screen")
class RegressionSet(unittest.TestCase):
    """The scripted half of the five-case regression set: intake and L1 must give the expected results."""

    def test_intake_and_l1(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = hiringcafe.process(hiringcafe.raw_responses(REG / "raw/hiringcafe"), out)
            self.assertEqual((result["unique"], result["truncated"], result["problems"]), (5, 1, []))
            jobs = {j["id"]: j for j in json.loads((out / "jobs.json").read_text())["jobs"]}
            crit = P.load_yaml(sample_env.CRITERIA)
            cond = P.load_yaml(sample_env.CRITERIA)["conditions"]
            l1 = {jid: P.screen_job(j, cond, out / "artifacts", {}, "2026-11-16", crit["search"]["max_posting_age_days"],
                                    crit["compensation"]["minimum_annual_usd"]) for jid, j in jobs.items()}
            get = lambda pid: l1[f"hiringcafe:{pid}"]
            self.assertEqual(get("d83uuiidimiciiq0")[0], "evaluation_error")
            self.assertIn("deadline 2026-09-30", get("d83uuiidimiciiq0")[1][0])
            self.assertEqual(get("zrbm4teerxql6oib")[0], "pass")
            self.assertIn("posting URL", " ".join(get("zrbm4teerxql6oib")[1]))
            self.assertEqual(jobs["hiringcafe:zrbm4teerxql6oib"]["travel_percent"], 25)
            self.assertEqual(get("hdbrlfvsrdsrck70")[0], "fail")
            self.assertEqual(get("94yr3y0bm60oa0w4")[0], "pass")
            self.assertEqual(get("53ay582qrnrfrelq")[0], "evaluation_error")
            expected = json.loads((REG / "expected.json").read_text())["jobs"]
            self.assertEqual(set(expected), set(jobs))


if __name__ == "__main__":
    unittest.main()

