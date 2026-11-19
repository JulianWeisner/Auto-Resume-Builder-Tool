"""Checks for the application tracker and its tool (tools/tracker.py).

Run: python3 -B -m unittest discover -s tools -p 'test_*.py'
Runs against a temporary copy of the fictional sample person's archive and tracker
(examples/sample-person), never your own.
"""
import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "examples" / "sample-person"
JOB = "Example-Freight-Co.Operations-Manager.2026-11-10"


def setUpModule():
    global ROOT, tracker
    ROOT = Path(tempfile.mkdtemp())
    for part in ("career", "applications", "tracker"):
        shutil.copytree(SAMPLE / part, ROOT / part)
    (ROOT / "tools").mkdir()
    for script in (REPO / "tools").glob("*.py"):
        shutil.copy2(script, ROOT / "tools" / script.name)
    os.environ["TRACKER_TZ"] = "America/New_York"
    spec = importlib.util.spec_from_file_location("sample_tracker", ROOT / "tools" / "tracker.py")
    tracker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tracker)


def tearDownModule():
    os.environ.pop("TRACKER_TZ", None)
    shutil.rmtree(ROOT, ignore_errors=True)


def entry(*events, archive=None):
    return {"id": "x", "company": "C", "role": "R", "archive": archive,
            "events": [{"date": d, "type": t, "source": "user"} for d, t in events]}


def queued_entry(job_id="queued-1", company="Lakeshore Supply", role="Warehouse Lead"):
    return {"id": job_id, "company": company, "role": role, "archive": None, "search_run": None,
            "posting_id": None, "posting_url": "https://example.com/jobs/" + job_id,
            "events": [{"date": "2026-11-12", "type": "queued", "source": "user"}]}


class StatusTests(unittest.TestCase):
    def test_furthest_step(self):
        self.assertEqual(tracker.status(entry(("2026-11-01", "queued"))), "queued")
        self.assertEqual(tracker.status(entry(("2026-11-01", "applied"), ("2026-11-02", "acknowledged"))), "acknowledged")
        self.assertEqual(tracker.status(entry(("2026-11-01", "applied"), ("2026-11-03", "screen"))), "in process")

    def test_final_event_wins_and_notes_do_not_count(self):
        e = entry(("2026-11-01", "applied"), ("2026-11-05", "rejected"), ("2026-11-06", "note"))
        self.assertEqual(tracker.status(e), "rejected")

    def test_event_order_does_not_depend_on_list_order(self):
        e = entry(("2026-11-05", "rejected"), ("2026-11-01", "applied"))
        self.assertEqual(tracker.status(e), "rejected")


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = tracker.load()

    def test_sample_tracker_is_valid(self):
        self.assertEqual(tracker.validate(self.ledger), [])
        job = next(e for e in self.ledger["applications"] if e["id"] == JOB)
        self.assertEqual(tracker.status(job), "in process")

    def test_every_archive_is_tracked(self):
        tracked = {e["archive"] for e in self.ledger["applications"] if e.get("archive")}
        self.assertEqual(tracked, set(tracker.archive_entries()))

    def test_missing_archive_is_an_error(self):
        broken = copy.deepcopy(self.ledger)
        broken["applications"] = [e for e in broken["applications"] if not e.get("archive")]
        self.assertTrue(any("missing from the tracker" in m for m in tracker.validate(broken)))

    def test_email_event_needs_saved_file(self):
        broken = copy.deepcopy(self.ledger)
        target = next(e for e in broken["applications"] if e.get("archive"))
        target["events"].append({"date": "2026-11-18", "type": "rejected", "source": "email"})
        self.assertTrue(any("email events need" in m for m in tracker.validate(broken)))

    def test_applied_without_archive_is_an_error(self):
        broken = copy.deepcopy(self.ledger)
        target = queued_entry()
        target["events"].append({"date": "2026-11-18", "type": "applied", "source": "user"})
        broken["applications"].append(target)
        self.assertTrue(any("applied needs an archive" in m for m in tracker.validate(broken)))

    def test_old_sources_are_rejected(self):
        broken = copy.deepcopy(self.ledger)
        broken["applications"][0]["events"].append({"date": "2026-11-18", "type": "note", "source": "someone"})
        self.assertTrue(any("source must be one of" in m for m in tracker.validate(broken)))


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.ledger = tracker.load()
        self.today = tracker.date(2026, 11, 18)

    def test_board_shows_applied_and_explains_the_empty_queue(self):
        frag = tracker.render_board(self.ledger, self.today, fragment=True)
        self.assertFalse(frag.startswith("<!DOCTYPE"))
        self.assertIn('<div class="sl">Applied</div><div class="sn">1</div>', frag)
        self.assertIn("Run a search to fill it", frag)

    def test_queued_jobs_list_and_drop_leaves_the_queue(self):
        led = copy.deepcopy(self.ledger)
        led["applications"] += [queued_entry("q1", "E. & J. Supply"), queued_entry("q2", "Harbor Parcel")]
        rows = tracker.queue_rows(led, self.today)
        self.assertEqual([r["id"] for r in rows], ["q1", "q2"])
        frag = tracker.render_board(led, self.today, fragment=True)
        self.assertIn("E. &amp; J. Supply", frag)
        self.assertEqual(frag.count('rel="noopener">Posting</a>'), 2)
        led["applications"][-1]["events"].append({"date": "2026-11-18", "type": "dropped", "source": "user"})
        self.assertNotIn("q2", {r["id"] for r in tracker.queue_rows(led, self.today)})

    def test_page_is_utf8_and_names_no_host(self):
        page = tracker.render_board(self.ledger, self.today)
        self.assertIn('<meta charset="utf-8">', page)
        self.assertNotIn("â€", page)
        self.assertNotIn("Claude", page)

    def test_stale_default_without_search_criteria(self):
        self.assertEqual(tracker.stale_after_days(), 21)

    def test_day_wording(self):
        self.assertEqual([tracker.days_ago(n) for n in (0, 1, 5)], ["today", "1 day ago", "5 days ago"])

    def test_update_queue_needs_a_finished_run(self):
        out = subprocess.run([tracker.sys.executable, str(ROOT / "tools/tracker.py"), "update-queue", "run", "c.json"],
                             capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("has no run.json", out.stderr)


class EventStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.events = self.tmp / "events"
        shutil.copytree(tracker.EVENTS, self.events)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def event(self, note="test", kind="interview"):
        return tracker.job_line(JOB, {"date": "2026-11-20", "type": kind, "source": "user", "note": note})

    def test_commit_adds_one_file_and_repeats_collapse(self):
        before = len(list(self.events.glob("*.json")))
        tracker.commit([self.event()], events=self.events)
        tracker.commit([self.event()], events=self.events)
        self.assertEqual(len(list(self.events.glob("*.json"))), before + 1)
        tracker.commit([self.event("no offer", "rejected")], events=self.events)
        job = next(e for e in tracker.load(self.events)["applications"] if e["id"] == JOB)
        self.assertEqual(tracker.status(job), "rejected")

    def test_edited_event_file_is_reported(self):
        path = sorted(self.events.glob("*.json"))[0]
        line = json.loads(path.read_text())
        line["note"] = "edited by hand"
        path.write_text(tracker.canonical(line))
        self.assertTrue(any("edited after it was written" in m for m in tracker.validate(tracker.load(self.events))))

    def test_two_branches_adding_events_merge_cleanly(self):
        repo = self.tmp / "repo"
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@example.com", "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "HOME": str(self.tmp)}
        git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)
        shutil.copytree(self.events, repo / "events")
        git("init", "-q", "-b", "main"); git("add", "."); git("commit", "-qm", "base")
        git("checkout", "-qb", "a")
        tracker.commit([self.event("branch a")], events=repo / "events"); git("add", "."); git("commit", "-qm", "a")
        git("checkout", "-q", "main"); git("checkout", "-qb", "b")
        tracker.commit([self.event("branch b"), self.event("branch a")], events=repo / "events")
        git("add", "."); git("commit", "-qm", "b")
        git("checkout", "-q", "main"); git("merge", "-q", "a"); git("merge", "-q", "--no-edit", "b")
        merged = tracker.load(repo / "events")
        job = next(e for e in merged["applications"] if e["id"] == JOB)
        self.assertEqual([ev.get("note") for ev in job["events"] if ev["type"] == "interview"].count("branch a"), 1)
        self.assertEqual(tracker.validate(merged), [])


class ShortcutTests(unittest.TestCase):
    """The shortcuts for Claude Code (.claude/skills), Codex (.agents/skills) and Gemini CLI (.gemini/commands)."""
    SKILLS = ("queue", "drop", "update-queue")

    def test_claude_and_codex_skills_are_identical(self):
        for name in self.SKILLS:
            codex = REPO / ".agents/skills" / name / "SKILL.md"
            claude = REPO / ".claude/skills" / name / "SKILL.md"
            self.assertEqual(codex.read_text(), claude.read_text(), name)
            self.assertIn(f"name: {name}\n", codex.read_text())

    @unittest.skipUnless(importlib.util.find_spec("tomllib"), "tomllib needs Python 3.11 or later")
    def test_gemini_commands_point_at_the_skills(self):
        import tomllib
        for name in self.SKILLS:
            cmd = tomllib.loads((REPO / ".gemini/commands" / f"{name}.toml").read_text())
            self.assertIn(f".agents/skills/{name}/SKILL.md", cmd["prompt"])
            self.assertIn("{{args}}", cmd["prompt"])

    def test_skills_name_real_commands_and_no_person(self):
        commands = {"board", "serve", "add-event", "update-queue"}
        text = "".join((REPO / ".agents/skills" / n / "SKILL.md").read_text() for n in self.SKILLS)
        for cmd in commands:
            self.assertIn(f"tracker.py {cmd}", text)
        parser_cmds = set(re.findall(r'add_parser\("([a-z-]+)"', (REPO / "tools/tracker.py").read_text()))
        self.assertTrue(commands <= parser_cmds)
        self.assertNotIn("Julian", text)


class EmailTests(unittest.TestCase):
    def test_render_keeps_body_and_ids(self):
        msg = {"id": "abc", "sender": "careers@example.com", "senderName": "Co", "toRecipients": ["a@example.com"],
               "date": "2026-11-02T03:00:00Z", "subject": "S", "plaintextBody": "Hi\n\nBody &nbsp;"}
        text = tracker.render_email(msg)
        self.assertIn("Gmail-Message-ID: abc", text)
        self.assertTrue(text.endswith("Hi\n\nBody &nbsp;\n"))
        self.assertIn("2026-11-01T22:00:00-05:00", text)  # the user's local date, not UTC

    def test_slug(self):
        self.assertEqual(tracker.slug("careers@example.com"), "careers-example-com")

    def test_sample_email_is_saved_unedited_with_its_hash(self):
        job = next(e for e in tracker.load()["applications"] if e["id"] == JOB)
        ev = next(ev for ev in job["events"] if ev["source"] == "email")
        self.assertEqual(tracker.sha256(ROOT / ev["file"]), ev["sha256"])


if __name__ == "__main__":
    unittest.main()
