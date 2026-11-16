"""Regression checks for the one-step résumé build.

Run: python3 -B -m unittest discover -s tools -p 'test_*.py'
Builds run in a temporary copy of the tools with the fictional sample person's
record (examples/sample-person), never your own record.
Skipped when Node.js with Playwright or poppler is unavailable.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "examples" / "sample-person"


def sample_repo():
    """A temporary repository: the tools plus the sample person's career record."""
    root = Path(tempfile.mkdtemp())
    shutil.copytree(SAMPLE / "career", root / "career")
    (root / "tools").mkdir()
    for script in (REPO / "tools").glob("*.py"):
        shutil.copy2(script, root / "tools" / script.name)
    return root


SAMPLE_ROOT = sample_repo()
TOOLS = SAMPLE_ROOT / "tools"
CONTACT = json.loads((SAMPLE_ROOT / "career/contact.json").read_text(encoding="utf-8"))


def tearDownModule():
    shutil.rmtree(SAMPLE_ROOT, ignore_errors=True)


def available():
    if not (shutil.which("node") and shutil.which("pdftotext")):
        return False
    return subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode == 0


def page(body, css=""):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: Letter; margin: .75in; }} body {{ font: 11pt/14pt Arial, sans-serif; }} p, li {{ margin: 0; }}
.keep {{ break-inside: avoid; }} {css}</style></head><body>
<h1>{CONTACT['name']}</h1><p>{CONTACT['location']} | {CONTACT['email']} | {CONTACT['phone']}</p>
<h2>Experience</h2>{body}<h2>Education</h2><p>Lakeside State University: BA, Economics | 2014</p>
<h2>Skills</h2><p>Process design | SQL</p></body></html>"""


def entry(i, bullets=3):
    items = "".join(f"<li>Ran work stream {i}.{b} with partner teams and shipped it on schedule.</li>"
                    for b in range(bullets))
    return f"<h3><span>Company {i}</span> <span>Jan 20{10 + i:02d} - Mar 20{11 + i:02d}</span></h3><ul>{items}</ul>"


@unittest.skipUnless(available(), "needs Node.js with Playwright and poppler")
class BuildResumeTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

    def build(self, name, html, *args, env=None):
        path = self.dir / name
        path.write_text(html, encoding="utf-8")
        r = subprocess.run([sys.executable, str(TOOLS / "build_resume.py"), str(path), *args],
                           capture_output=True, text=True,
                           env={**os.environ, "RESUME_TOOL_ENV": "off", **(env or {})})
        return r.returncode, r.stdout + r.stderr, path.with_suffix(".pdf")

    def test_year_range_in_a_bullet_is_prose(self):
        body = entry(1) + "<ul><li>Grew repeat orders each year from 2021–2023 across three partner channels.</li></ul>"
        code, out, _ = self.build("prose.html", page(body + entry(2)))
        self.assertEqual(code, 0, out)

    def test_python_reader_matches_poppler(self):
        sys.path.insert(0, str(TOOLS))
        import resume_check
        if not (resume_check.PythonReader.available() and resume_check.Poppler.available()):
            self.skipTest("needs both PDF readers")
        code, out, pdf = self.build("same.html", page("".join(entry(i) for i in range(1, 4))))
        self.assertEqual(code, 0, out)
        results = []
        for reader in ("poppler", "python"):
            r = subprocess.run([sys.executable, str(TOOLS / "resume_check.py"), str(pdf),
                                "--source", str(pdf.with_suffix(".html"))], capture_output=True, text=True,
                               env={**os.environ, "RESUME_PDF_READER": reader, "RESUME_TOOL_ENV": "off"})
            results.append([l for l in r.stdout.splitlines() if "characters" not in l])
        self.assertEqual(results[0], results[1])

    def test_blocked_browser_is_named(self):
        fake = self.dir / "chrome"
        fake.write_text("#!/bin/sh\necho 'Operation not permitted' >&2\nexit 1\n")
        fake.chmod(0o755)
        code, out, _ = self.build("b.html", page(entry(1)),
                                  env={"BUILD_RESUME_RENDERER": "chrome", "CHROME_PATH": str(fake)})
        self.assertEqual(code, 2, out)
        self.assertIn("BUILD CANNOT RUN (blocked)", out)

    def test_chrome_fallback_renders(self):
        sys.path.insert(0, str(TOOLS))
        import build_resume
        if not build_resume.find_chrome():
            self.skipTest("no Chrome or Chromium installed")
        code, out, pdf = self.build("c.html", page(entry(1)), env={"BUILD_RESUME_RENDERER": "chrome"})
        self.assertEqual(code, 0, out)
        self.assertIn("rendered with Chrome", out)
        text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        self.assertNotIn("file://", text)

    def test_missing_renderer_is_a_setup_error(self):
        code, out, _ = self.build("m.html", page(entry(1)),
                                  env={"BUILD_RESUME_RENDERER": "chrome", "CHROME_PATH": "/nonexistent"})
        self.assertEqual(code, 2, out)
        self.assertIn("BUILD CANNOT RUN (missing)", out)
        self.assertIn("--setup", out)

    def test_check_setup_reports_ready(self):
        r = subprocess.run([sys.executable, str(TOOLS / "build_resume.py"), "--check-setup"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("READY", r.stdout)

    def test_clean_build_passes_and_saves_snapshot(self):
        notes = self.dir / "sources.md"
        notes.write_text("Company 1 bullet 1 -> NW-EXP-002\n", encoding="utf-8")
        code, out, pdf = self.build("ok.html", page("".join(entry(i) for i in range(1, 4))),
                                    "--snapshot", str(notes))
        self.assertEqual(code, 0, out)
        self.assertIn("BUILD OK", out)
        code, out, _ = self.build("ok.html", page("".join(entry(i) for i in range(1, 4))),
                                  "--snapshot", str(notes))  # a revision replaces the snapshot
        self.assertEqual(code, 0, out)
        snaps = [p for p in self.dir.iterdir() if "snapshot" in p.name]
        self.assertEqual([p.name for p in snaps], ["ok-snapshot"])
        manifest = json.loads((snaps[0] / "manifest.json").read_text())
        self.assertIn("sources.md", manifest["files"])
        self.assertIn(pdf.name, manifest["files"])
        self.assertIn("ok.check.txt", manifest["files"])

    def test_proof_report_from_snapshot(self):
        notes = self.dir / "sources.md"
        notes.write_text("Company 1 bullet -> NW-EXP-002\nMade-up claim -> NOT-A-REAL-001\nNo source line\n",
                         encoding="utf-8")
        plan = self.dir / "plan.md"
        plan.write_text("- Source: main at abc123\n- Review before build: dates confirmed\n", encoding="utf-8")
        code, out, _ = self.build("p.html", page(entry(1)), "--snapshot", str(notes), str(plan))
        self.assertEqual(code, 0, out)
        r = subprocess.run([sys.executable, str(TOOLS / "proof_report.py"), str(self.dir / "p-snapshot")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        report = (self.dir / "p-snapshot" / "proof.html").read_text(encoding="utf-8")
        self.assertIn("NW-EXP-002</b> · Returns process redesign", report)  # known record shows its title
        self.assertIn("Limits: Shared with three shift supervisors", report)  # and its limits
        self.assertIn("NOT-A-REAL-001</b> <span class='muted'>record not found", report)
        self.assertIn("no record named", report)              # a line with no source is flagged
        self.assertIn("dates confirmed", report)
        self.assertIn("main at abc123", report)

    def test_overflow_is_measured_and_blocks_snapshot(self):
        notes = self.dir / "sources.md"
        notes.write_text("x\n", encoding="utf-8")
        code, out, _ = self.build("long.html", page("".join(entry(i, 8) for i in range(1, 16))),
                                  "--snapshot", str(notes))
        self.assertEqual(code, 1)
        self.assertRegex(out, r"pages, target 2: about \d+ lines over")
        self.assertIn("Snapshot not saved", out)
        self.assertEqual([p for p in self.dir.iterdir() if "snapshot" in p.name], [])

    def test_stranded_heading_is_found_and_keep_fixes_it(self):
        # Slide a heading toward the page bottom (no keep-with-next CSS) until it strands;
        # font metrics differ by machine, so search rather than hard-code the position.
        bullets = "".join(f"<li>Item {b} with a full line of descriptive text.</li>" for b in range(6))
        for n in range(30, 70):
            filler = "".join(f"<p>Filler line {i}, Jan 2020 - Mar 2021.</p>" for i in range(n))
            heading = "<h3><span>NORTHWIND LOGISTICS</span></h3>"
            code, out, pdf = self.build(f"s{n}.html", page(filler + heading + f"<ul>{bullets}</ul>"))
            if 'stranded at the bottom of page 1: "northwind logistics"' in out:
                break
        else:
            self.fail("no stranding layout found to test")
        first = subprocess.run(["pdftotext", "-f", "1", "-l", "1", str(pdf), "-"], capture_output=True, text=True)
        self.assertEqual([l for l in first.stdout.splitlines() if l.strip()][-1].strip(), "NORTHWIND LOGISTICS")
        kept = filler + f'<div class="keep">{heading}<ul><li>Item 0 with a full line.</li></ul></div><ul>{bullets}</ul>'
        _, out, _ = self.build("kept.html", page(kept))
        self.assertNotIn('"northwind logistics"', out)


class TermRuleTests(unittest.TestCase):
    """No PDF needed: the terms file rules."""

    def test_evidence_phrase_is_not_an_alternative(self):
        sys.path.insert(0, str(TOOLS))
        import resume_check
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / "tags.json").write_text(json.dumps({"Do-5": {"text": "Instrument adoption, trust, and quality"}}))
        (d / "terms.txt").write_text("Do-5 | adoption / used by Acme\nDo-5 | quality / QA\n")
        rows, errors = resume_check.check_terms("quality adoption", d / "tags.json", d / "terms.txt")
        self.assertEqual(len(errors), 1)
        self.assertIn("reads as evidence", errors[0])
        self.assertEqual(rows[0]["status"], "covered")  # QA is a fine abbreviation


if __name__ == "__main__":
    unittest.main()
