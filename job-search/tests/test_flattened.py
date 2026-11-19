"""Flattened provider descriptions (a whole posting in one paragraph) and provider stubs."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import jd_ingest as J  # noqa: E402
import pipeline as P  # noqa: E402

SENTENCES = ["About Acme: we build kitchen tools for home cooks and professional chefs across North America.",
             "You will own the roadmap for our connected cookware and work closely with engineering and design.",
             "What you'll do: • Lead discovery with customers and partners • Define success metrics and run experiments",
             "• Ship releases every quarter with the firmware team.",
             "Requirements: 5+ years of product management experience with consumer hardware.",
             "Experience with Bluetooth devices is a plus.",
             "This role is hybrid in New York City, three days a week."]
FLAT = " ".join(SENTENCES * 4)  # one line, well over SENTENCE_SPLIT_MIN code points


class Flattened(unittest.TestCase):
    def test_one_paragraph_is_split_into_sentence_blocks(self):
        self.assertGreater(len(FLAT), J.SENTENCE_SPLIT_MIN)
        art, norm = J.ingest(FLAT, "hiringcafe", {"provider_job_id": "x"})
        self.assertEqual(art["normalization"]["method"], "line_blocks+sentences+wrap")
        blocks = [FLAT[b["source"][0]:b["source"][1]] for b in art["blocks"]]
        self.assertGreater(len(blocks), 20)
        self.assertIn("Requirements: 5+ years of product management experience with consumer hardware.", blocks)
        self.assertIn("• Lead discovery with customers and partners", blocks)
        self.assertTrue(all(b == b.strip() and b for b in blocks))
        # Insert-only: removing the inserted newlines gives back the source exactly.
        self.assertEqual(J.reconstruct(art, norm)[0], FLAT)
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / art["artifact_id"]
            J.write_artifact(d, art, norm)
            self.assertEqual(J.validate_dir(d)[2], [])
            # Each sentence can now be tagged or skipped as a whole block.
            first = next(b for b in art["blocks"] if FLAT[b["source"][0]:b["source"][1]].startswith("Requirements"))
            mapping = []
            for b in art["blocks"]:
                ba, bz = b["lines"]
                tag = "Want-1" if b is first else "skip"
                rng = f"L{ba}" if ba == bz else f"L{ba}-L{bz}"
                mapping.append(f"{tag} {rng}" + ("" if tag != "skip" else " test"))
            code, _, errors, stderr = J.render(d, "\n".join(mapping) + "\n")
            self.assertEqual((code, errors), (0, []), stderr)

    def test_normal_postings_are_unchanged(self):
        text = "\n".join(SENTENCES) + "\n"
        art, _ = J.ingest(text, "hiringcafe", {"provider_job_id": "x"})
        self.assertEqual(art["normalization"]["method"], "line_blocks+wrap")
        self.assertEqual(len([b for b in art["blocks"] if b["kind"] == "content"]), len(SENTENCES))


class Stub(unittest.TestCase):
    def test_provider_stub_is_insufficient_and_fails_l1(self):
        art, norm = J.ingest("FELFEL 2849570-15134", "hiringcafe", {"provider_job_id": "e4j"}, completeness="complete")
        self.assertEqual(art["source"]["completeness"], {"status": "insufficient", "basis": "too_few_words", "words": 2})
        with tempfile.TemporaryDirectory() as tmp:
            J.write_artifact(Path(tmp) / art["artifact_id"], art, norm)
            self.assertEqual(J.validate_dir(Path(tmp) / art["artifact_id"])[2], [])
            job = {"location": "New York, NY", "workplace": "Onsite", "jd_artifact": {"artifact_id": art["artifact_id"]}}
            result, reasons = P.screen_job(job, P.load_yaml(sample_env.CRITERIA)["conditions"], tmp)
            self.assertEqual(result, "evaluation_error")
            self.assertIn("too short", reasons[0])

    def test_pasted_text_is_not_judged_by_length(self):
        art, _ = J.ingest("Short pasted note.", "user_paste")
        self.assertEqual(art["source"]["completeness"], {"status": "unknown"})


class ChoicesFile(unittest.TestCase):
    def test_readable_choices_file_imports_and_queue_flags_missing_choices(self):
        import json
        run = json.loads((ROOT / "tests/fixtures/sample_run.json").read_text())
        for j in run["jobs"]:
            j["decision"] = "undecided"
        self.assertFalse(P.export_queue(run)["choices_imported"])
        jid = run["jobs"][0]["id"]
        choices = {"kind": "decisions", "run_id": run["run_id"], "decisions": {jid: "interested"},
                   "jobs": {jid: {"company": "Acme", "title": "PM", "url": "https://example.org", "label": None,
                                  "fit": None, "requirements_met": None}}}
        self.assertEqual(P.apply_decisions(run, choices)["interested"], 1)
        self.assertTrue(P.export_queue(run)["choices_imported"])
        self.assertIn("jobs: Object.fromEntries", (ROOT / "tools/cards.html").read_text())


if __name__ == "__main__":
    unittest.main()
