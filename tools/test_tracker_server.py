"""Checks for the local tracker server (tracker.py serve): saving works and only this page can save.

Run: python3 -B -m unittest discover -s tools -p 'test_*.py'
Uses the synthetic search run in job-search/tests/fixtures/ and temporary event folders, never your own.
"""
import json
import os
import shutil
import subprocess
import sys
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
os.environ.setdefault("ARB_CAREER_REPO", str(REPO / "examples" / "sample-person"))  # pipeline runs read the sample person

import tracker  # noqa: E402
import tracker_server  # noqa: E402

FIXTURE_RUN = REPO / "job-search" / "tests" / "fixtures" / "sample_run.json"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(tracker.EVENTS, self.tmp / "events")
        (self.tmp / "runs").mkdir()
        # A finished run that is not saved yet: the synthetic fixture run, its cards and an empty artifacts folder.
        self.run = self.tmp / "work" / "test-run"
        (self.run / "artifacts").mkdir(parents=True)
        run = json.loads(FIXTURE_RUN.read_text())
        run["run_id"] = "test-run"
        (self.run / "run.json").write_text(json.dumps(run))
        subprocess.run([sys.executable, str(tracker.PIPELINE), "cards", str(self.run / "run.json"),
                        "-o", str(self.run / "cards.html")], check=True, capture_output=True)
        self.patches = [mock.patch.object(tracker, "EVENTS", self.tmp / "events"),
                        mock.patch.object(tracker, "RUNS", self.tmp / "runs")]
        for p in self.patches:
            p.start()
        # Two queued jobs from an earlier, made-up search.
        tracker.commit([tracker.job_line(f"example:{n}", {"date": "2026-11-12", "type": "queued", "source": "search-run"},
                                         company=f"Example {n} Co", role="Operations Manager", posting_id=f"example:{n}",
                                         posting_url=f"https://example.com/jobs/{n}") for n in ("one", "two")])
        self.port = free_port()
        self.server = tracker_server.ThreadingHTTPServer(
            ("127.0.0.1", self.port), tracker_server.make_handler(self.run, self.port))
        self.server.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp)

    def get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}").read().decode()

    def post(self, path, body, origin=None):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", json.dumps(body).encode(), headers)
        try:
            return 200, json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def queued(self):
        return [e for e in tracker.load()["applications"] if tracker.status(e) == "queued"]

    def test_board_and_cards_are_served_with_working_buttons(self):
        board = self.get("/")
        self.assertIn("window.TRACKER_SERVED=true", board)
        self.assertEqual(board.count('data-kind="drop"'), len(self.queued()))
        self.assertIn('id="uq"', self.get("/cards"))

    def test_drop_writes_one_event_with_the_reason(self):
        job = self.queued()[0]["id"]
        code, reply = self.post("/api/drop", {"job": job, "reason": "Posting too old"},
                                origin=f"http://127.0.0.1:{self.port}")
        self.assertEqual((code, reply["ok"]), (200, True))
        dropped = next(e for e in tracker.load()["applications"] if e["id"] == job)
        self.assertEqual(tracker.status(dropped), "dropped")
        self.assertEqual(dropped["events"][-1]["note"], "Posting too old")
        self.assertEqual(self.post("/api/drop", {"job": job})[0], 409)  # already gone from the queue

    def test_update_queue_saves_the_run_and_queues_interested_jobs(self):
        run = json.loads((self.run / "run.json").read_text())
        fresh = [j["id"] for j in run["jobs"] if j.get("decision") in (None, "undecided")][:2]
        self.assertEqual(len(fresh), 2)
        choices = {"kind": "decisions", "run_id": "test-run", "decisions": {i: "interested" for i in fresh}}
        before = len(self.queued())
        code, reply = self.post("/api/update-queue", {"choices": choices})
        self.assertEqual((code, reply["ok"]), (200, True), reply)
        self.assertTrue((self.tmp / "runs" / "test-run" / "application_queue.json").exists())
        self.assertEqual(len(self.queued()), before + 2)
        self.assertEqual(self.post("/api/update-queue", {"choices": choices})[0], 400)  # never overwrites

    def test_only_this_page_can_save(self):
        job = self.queued()[0]["id"]
        self.assertEqual(self.post("/api/drop", {"job": job}, origin="https://example.com")[0], 403)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/drop", b"job=x",
                                     {"Content-Type": "application/x-www-form-urlencoded"})
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req)
        self.assertEqual(err.exception.code, 415)
        self.assertEqual(len(self.queued()), len([e for e in tracker.load()["applications"]
                                                  if tracker.status(e) == "queued"]))


    def test_other_hosts_are_refused(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", headers={"Host": "attacker.example.com"})
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req)
        self.assertEqual(err.exception.code, 421)

    def test_busy_port_moves_to_the_next(self):
        server, port = tracker_server.bind(self.port, None)
        try:
            self.assertNotEqual(port, self.port)
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()
