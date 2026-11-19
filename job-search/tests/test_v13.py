"""Schema 1.3: dates and deadlines, the card object, nice-to-have weight, L1 location and age gates,
the cards page, decisions and HiringCafe intake."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hiringcafe  # noqa: E402
import pipeline as P  # noqa: E402
from test_funnel import ask  # noqa: E402

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover
    yaml = None

CARD = {"business": "Sells sleep earbuds to consumers.", "owns": "The core app and firmware roadmap.",
        "responsibilities": ["Own the roadmap.", "Ship releases."], "level": "Director"}


def job13(jid, reqs, **kw):
    route, gaps = P.routing(reqs), P.critical_gaps(reqs)
    mand = [r for r in reqs if r.get("mandatory")]
    elig = "pass" if all(r["qualification_status"] == "supported" for r in mand) else "unresolved"
    status = "deprioritized" if route == "deprioritized" else "eligible" if elig == "pass" else "needs_verification"
    f = P.fit(reqs)
    j = {"id": jid, "provider": "hiringcafe", "company": jid, "title": "PM", "posting_url": f"https://hiringcafe.com/job/x-{jid}",
         "status": status, "decision": "undecided", "fit_percent": f, "functional_fit": f, "eligibility": elig,
         "application_confidence": "medium", "confidence_reason": "reason", "requirements": reqs, "exclusion": None,
         "posted_date": "2026-11-01", "card": copy.deepcopy(CARD), "strongest_evidence": "Owned a consumer app.",
         "screen": {"critical_gaps": gaps, "routing": route, "reason": "two gaps" if route == "deprioritized" else None}}
    j.update(kw)
    return j


def run13(*jobs):
    return {"schema_version": "1.3", "run_id": "t", "run_date": "2026-11-16", "source_commit": "0" * 40,
            "search_criteria": "x", "discovered_count": len(jobs), "duplicate_count": 0, "jobs": list(jobs)}


class Schema13(unittest.TestCase):
    def setUp(self):
        self.run = run13(job13("a", [ask("x", 4), ask("y", 3, defining=True)]),
                         job13("b", [ask("x", 1), ask("y", 3)]))

    def test_valid(self):
        self.assertEqual(P.validate(self.run), [])

    def test_nice_half_weight(self):
        reqs = [ask("a", 4), ask("b", 1, kind="nice", mandatory=False)]
        self.assertEqual(P.fit(reqs), round((1 + 0.25 * 0.5) / 1.5 * 100))

    def test_dates(self):
        r = copy.deepcopy(self.run); r.pop("run_date")
        self.assertTrue(any("run_date" in e for e in P.validate(r)))
        r = copy.deepcopy(self.run); r["jobs"][0].pop("posted_date")
        self.assertTrue(any("posted_date" in e for e in P.validate(r)))
        r = copy.deepcopy(self.run); r["jobs"][0]["deadline"] = "2026-09-30"
        self.assertTrue(any("status must be evaluation_error" in e for e in P.validate(r)))
        r["jobs"][0].update(status="evaluation_error", fit_percent=None, functional_fit=None, eligibility=None,
                            application_confidence=None, card=None)
        self.assertTrue(any("error_reason" in e for e in P.validate(r)))
        r["jobs"][0]["error_reason"] = "application deadline 2026-09-30 has passed"
        self.assertEqual(P.validate(r), [])

    def test_card_required_without_filler(self):
        r = copy.deepcopy(self.run); r["jobs"][0].pop("card")
        self.assertTrue(any("card object" in e for e in P.validate(r)))
        r = copy.deepcopy(self.run); r["jobs"][0]["card"]["team"] = ""
        self.assertTrue(any("leave out" in e for e in P.validate(r)))
        r = copy.deepcopy(self.run); r["jobs"][0]["card"]["responsibilities"] = ["a", "b", "c", "d"]
        self.assertTrue(any("1-3" in e for e in P.validate(r)))

    def test_deprioritized_needs_no_assessment(self):
        d = job13("d", [ask("x", 0), ask("y", 1)], fit_percent=None, functional_fit=None, eligibility=None,
                  application_confidence=None, confidence_reason=None, card=None)
        self.assertEqual(P.validate(run13(d)), [])

    def test_must_haves_defining_first(self):
        self.assertEqual(P.must_haves(self.run["jobs"][0]), ["quote y", "quote x"])

    def test_cards_page_and_decisions(self):
        page = P.render_cards(self.run)
        self.assertIn("<title>Job Review Queue</title>", page)
        self.assertNotIn("/*DATA*/null", page)
        data = P.card_data(self.run)
        self.assertEqual([c["id"] for c in data["cards"]], ["a", "b"])
        self.assertEqual(data["cards"][0]["age"], 15)
        self.assertEqual(data["cards"][1]["gaps"], ["quote x"])
        r = copy.deepcopy(self.run)
        self.assertEqual(P.apply_decisions(r, {"a": "interested"})["interested"], 1)
        with self.assertRaises(ValueError):
            P.apply_decisions(r, {"zz": "pass"})

    def test_page_escapes_script_end(self):
        r = copy.deepcopy(self.run); r["jobs"][0]["card"]["business"] = "</script><b>x"
        self.assertNotIn("</script><b>", P.render_cards(r))

    def test_quote_tolerance(self):
        self.assertEqual(P.loose("Don’t stop  now"), "Don't stop now")


@unittest.skipUnless(yaml, "PyYAML needed for screen")
class Screen13(unittest.TestCase):
    def setUp(self):
        self.cond = P.load_yaml(sample_env.CRITERIA)["conditions"]

    def test_whole_word_regions(self):
        j = {"location": "Seattle or Indianapolis", "workplace": "Remote"}
        self.assertEqual(P.screen_job(j, self.cond)[0], "pass")
        # Remote roles outside the US are asked about, not failed.
        self.assertEqual(P.screen_job({"location": "Bangalore, India", "workplace": "Remote"}, self.cond)[0], "unknown")

    def test_state_from_url(self):
        j = {"provider": "hiringcafe", "location": "Morristown or Atlanta", "workplace": "Hybrid",
             "posting_url": "https://hiringcafe.com/job/sr-product-strategy-manager-zelis-morristown-new-jersey-zrbm4?utm_source=x"}
        self.assertEqual(P.screen_job(j, self.cond)[0], "pass")
        j["posting_url"] = "https://hiringcafe.com/job/pm-acme-atlanta-georgia-abc"
        # The URL places only Atlanta; "Morristown" alone cannot be placed, so ask.
        self.assertEqual(P.screen_job(j, self.cond)[0], "unknown")
        j["location"] = "Atlanta"
        self.assertEqual(P.screen_job(j, self.cond)[0], "fail")

    def test_age_and_deadline(self):
        j = {"location": "New York", "workplace": "Hybrid", "posted_date": "2026-09-01"}
        self.assertEqual(P.screen_job(j, self.cond, run_date="2026-11-16", max_age_days=30)[0], "evaluation_error")
        j["posted_date"] = "2026-11-01"
        self.assertEqual(P.screen_job(j, self.cond, run_date="2026-11-16", max_age_days=30)[0], "pass")
        j["deadline"] = "2026-09-30"
        self.assertEqual(P.screen_job(j, self.cond, run_date="2026-11-16")[0], "evaluation_error")

    def test_criteria(self):
        c = P.load_yaml(sample_env.CRITERIA)
        self.assertEqual(c["search"]["max_posting_age_days"], 30)
        self.assertEqual(c["compensation"]["minimum_annual_usd"], 100000)
        ids = [f["id"] for f in c["search"]["role_families"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(f["tier"] in {"core", "strong", "exploratory", "broad"} and f["titles"]
                            for f in c["search"]["role_families"]))
        domains = {d["id"] for d in c["search"]["domains"]}
        self.assertLessEqual(set(c["providers"]["hiringcafe"]["domain_industries"]), domains)

    def test_pay_floor(self):
        self.assertEqual(P.pay_top("$93,500 – $177,590/yr"), 177590)
        self.assertEqual(P.pay_top("$60/hr"), 124800)
        self.assertIsNone(P.pay_top(None))
        j = {"location": "New York", "workplace": "Hybrid", "compensation": "$94,000 – $99,000/yr"}
        self.assertEqual(P.screen_job(j, self.cond, min_pay=100000)[0], "fail")
        j["compensation"] = "$93,500 – $177,590/yr"
        self.assertEqual(P.screen_job(j, self.cond, min_pay=100000)[0], "pass")
        j["compensation"] = None
        self.assertEqual(P.screen_job(j, self.cond, min_pay=100000)[0], "pass")


class Intake(unittest.TestCase):
    RESPONSE = ("# [Product Manager](https://hiringcafe.com/job/pm-acme-new-york-city-new-york-abc123?utm_source=claude)\n"
                "**Acme**\n\n- **Location:** New York City\n- **Workplace:** Hybrid\n- **Compensation:** $150,000/yr\n"
                "- **Posted:** 2026-11-01\n- **Job ID:** abc123\n\n## Requirements summary\nStuff.\n\n"
                "## Full description\nAbout Acme\n\nAcme sells anvils and other heavy tools to customers across the country. The product manager owns the roadmap, works with engineering and design, and reports on adoption every quarter.\n")

    def transcript(self, tmp, responses):
        lines = []
        for n, (jid, text) in enumerate(responses):
            lines.append({"message": {"content": [{"type": "tool_use", "id": f"t{n}",
                          "name": f"mcp__{'HiringCafe_Job_Search' if n % 2 else 'a1b2c3'}__get_job_details",
                          "input": {"job_id": jid}}]}})
            lines.append({"timestamp": "2026-11-16T01:00:00Z", "message": {"content": [
                {"type": "tool_result", "tool_use_id": f"t{n}", "content": [{"type": "text", "text": text}]}]}})
        path = Path(tmp) / "t.jsonl"
        path.write_text("\n".join(json.dumps(x) for x in lines))
        return path

    def test_extract_dedupes_and_saves_verbatim(self):
        repost = self.RESPONSE.replace("abc123", "zzz999")
        truncated = self.RESPONSE.replace("abc123", "trunc1").replace("Acme**", "Beta**").replace(
            "quarter.\n", "quarter.\n\n…(truncated — read the full posting at https://hiringcafe.com/job/trunc1)")
        with tempfile.TemporaryDirectory() as tmp:
            path = self.transcript(tmp, [("abc123", self.RESPONSE), ("abc123", self.RESPONSE),
                                         ("zzz999", repost), ("trunc1", truncated)])
            out = Path(tmp) / "run"
            result = hiringcafe.extract(path, out)
            self.assertEqual((result["responses"], result["unique"], result["duplicates"], result["truncated"]), (4, 2, 2, 1))
            jobs = json.loads((out / "jobs.json").read_text())["jobs"]
            self.assertEqual(jobs[0]["aliases"], ["hiringcafe:zzz999"])
            self.assertEqual((jobs[0]["posted_date"], jobs[0]["workplace"]), ("2026-11-01", "Hybrid"))
            self.assertEqual((out / "raw/hiringcafe/abc123.md").read_text(), self.RESPONSE)
            self.assertEqual([j["completeness"] for j in jobs], ["complete", "truncated"])

    def test_stated_terms(self):
        t = hiringcafe.stated_terms("The expected application deadline for this job is September 30, 2026. "
                                    "Travel up to 25%, occasionally 40% travel.")
        self.assertEqual((t["deadline"], t["travel_percent"]), ("2026-09-30", 40))
        self.assertIn("September 30", t["extracted"]["deadline"])
        self.assertEqual(hiringcafe.stated_terms("Application Close Date: 12/31/2026")["deadline"], "2026-12-31")
        self.assertEqual(hiringcafe.stated_terms("No dates here."), {})

    def test_empty_transcript_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.transcript(tmp, [])
            self.assertEqual(hiringcafe.main(["extract", str(path), str(Path(tmp) / "run")]), 1)


if __name__ == "__main__":
    unittest.main()
