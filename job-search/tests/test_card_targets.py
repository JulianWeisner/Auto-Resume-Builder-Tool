"""Card targets: the user names review cards; the run fetches 1.5x, tops up in batches, caps at 3x."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pipeline as P  # noqa: E402

SEARCH = {"title_stopwords": [], "max_posting_age_days": 30, "first_batch_multiplier": 1.5,
          "max_fetch_multiplier": 3, "top_up_batch_min": 2,
          "role_families": [{"id": "pm", "tier": "core", "titles": ["product manager"]},
                            {"id": "cos", "tier": "strong", "titles": ["chief of staff"]}]}
CRITERIA = {"search": SEARCH}


def item(n, fam):
    title = "Product Manager" if fam == "pm" else "Chief of Staff"
    return {"job_id": f"{fam}{n}", "company": f"Co{fam}{n}", "title": title, "posted_date": "2026-11-10",
            "location": f"City {n}"}


class CardTargets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        self.plan = {"workflow_version": 2, "criteria": CRITERIA, **P.card_budget(SEARCH, 4),
                     "searches": [{"id": "pm:1", "family": "pm", "tier": "core", "text": "product manager"},
                                  {"id": "cos:1", "family": "cos", "tier": "strong", "text": "chief of staff"}]}
        self.log = {"searches": [{"id": "pm:1", "status": "run", "items": [item(i, "pm") for i in range(10)]},
                                 {"id": "cos:1", "status": "run", "items": [item(i, "cos") for i in range(10)]}]}
        (self.d / "plan.json").write_text(json.dumps(self.plan))
        (self.d / "search_log.json").write_text(json.dumps(self.log))

    def tearDown(self): self.tmp.cleanup()

    def fetch(self, ids, labels):
        """Simulate intake and evaluation: one job per id, a result carrying the given label."""
        jobs = json.loads((self.d / "jobs.json").read_text())["jobs"] if (self.d / "jobs.json").exists() else []
        jobs += [{"id": f"hiringcafe:{i}", "provider": "hiringcafe", "company": i, "title": "t"} for i in ids]
        (self.d / "jobs.json").write_text(json.dumps({"discovered": len(jobs), "duplicates": 0, "jobs": jobs}))
        (self.d / "results").mkdir(exist_ok=True)
        for i, label in zip(ids, labels):
            (self.d / "results" / f"hiringcafe_{i}.json").write_text(json.dumps({"id": f"hiringcafe:{i}", "label": label}))

    def test_budget(self):
        self.assertEqual(P.card_budget(SEARCH, 10), {"target_cards": 10, "first_batch": 15, "fetch_cap": 30, "top_up_min": 2})
        with self.assertRaises(ValueError): P.card_budget(SEARCH, 0)

    def test_larger_target_keeps_earlier_picks(self):
        small = P.candidates(self.plan, self.log, CRITERIA, "2026-11-17")
        self.assertEqual(len(small["selected"]), 6)  # first batch: 1.5 x 4 cards
        big = P.candidates(self.plan, self.log, CRITERIA, "2026-11-17", 11)
        self.assertEqual(big["selected"][:6], small["selected"])
        capped = P.candidates(self.plan, self.log, CRITERIA, "2026-11-17", 50)
        self.assertEqual(len(capped["selected"]), 12)  # never more than 3 x 4 cards

    def test_top_up_until_cards_are_reached(self):
        first = P.candidates(self.plan, self.log, CRITERIA, "2026-11-17")
        (self.d / "candidates.json").write_text(json.dumps(first))
        self.fetch(first["selected"][:3], [])  # three fetched, none evaluated yet
        manifest = P.freeze(json.loads((self.d / "jobs.json").read_text()), "r", "2026-11-17", "a" * 40)
        (self.d / "manifest.json").write_text(json.dumps(manifest))
        self.assertEqual(P.top_up(self.d)["action"], "evaluate")
        # The full first batch: 6 fetched and evaluated, 2 cards.
        for f in (self.d / "results").glob("*"): f.unlink()
        self.fetch(first["selected"][3:], [])
        jobs = json.loads((self.d / "jobs.json").read_text())
        added = P.add_batch(manifest, jobs)
        self.assertEqual(len(added), 3)
        (self.d / "manifest.json").write_text(json.dumps(manifest))
        for i, label in zip(first["selected"], ["Promising", "Deprioritize", "Stretch", None, "Deprioritize", "Deprioritize"]):
            (self.d / "results" / f"hiringcafe_{i}.json").write_text(json.dumps({"id": f"hiringcafe:{i}", "label": label}))
        prog = P.card_progress(self.d)
        self.assertEqual((prog["cards"], prog["evaluated"], prog["fetched"], prog["target_met"]), (2, 6, 6, False))
        step = P.top_up(self.d)
        self.assertEqual(step["action"], "fetch")
        self.assertEqual(len(step["fetch"]), 3)  # max(2, ceil(2 cards short x 1.5))
        cand = json.loads((self.d / "candidates.json").read_text())
        self.assertEqual(cand["selected"][:6], first["selected"])
        self.assertEqual(cand["batches"], [first["selected"], step["fetch"]])
        # Second batch evaluated: two more cards reach the target.
        self.fetch(step["fetch"], ["Promising", "Stretch", "Deprioritize"])
        P.add_batch(manifest, json.loads((self.d / "jobs.json").read_text()))
        (self.d / "manifest.json").write_text(json.dumps(manifest))
        done = P.top_up(self.d)
        self.assertEqual((done["action"], done["reason"], done["cards"]), ("none", "card target reached", 4))
        self.assertEqual(len(manifest["batches"]), 3)

    def test_exhausted_pool_ends_short_and_says_why(self):
        self.log = {"searches": [{"id": "pm:1", "status": "run", "items": [item(i, "pm") for i in range(3)]},
                                 {"id": "cos:1", "status": "run", "items": []}]}
        (self.d / "search_log.json").write_text(json.dumps(self.log))
        first = P.candidates(self.plan, self.log, CRITERIA, "2026-11-17")
        self.assertEqual(len(first["selected"]), 3)
        (self.d / "candidates.json").write_text(json.dumps(first))
        self.fetch(first["selected"], ["Promising", "Deprioritize", "Deprioritize"])
        (self.d / "manifest.json").write_text(json.dumps(P.freeze(json.loads((self.d / "jobs.json").read_text()), "r", "2026-11-17", "a" * 40)))
        done = P.top_up(self.d)
        self.assertEqual((done["action"], done["reason"]), ("none", "search results exhausted; 1 of 4 cards"))

    def test_add_batch_refuses_changed_inputs(self):
        jobs = {"jobs": [{"id": "hiringcafe:a", "company": "A"}]}
        manifest = P.freeze(jobs, "r", "2026-11-17", "a" * 40)
        jobs["jobs"][0]["company"] = "changed"
        with self.assertRaises(ValueError): P.add_batch(manifest, jobs)


if __name__ == "__main__":
    unittest.main()
