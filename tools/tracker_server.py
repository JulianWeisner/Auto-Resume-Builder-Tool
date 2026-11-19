"""Local tracker server: the queue board and a run's review cards, with buttons that save.

Started by `python3 tools/tracker.py serve [--run RUN] [--port 8765]`. It listens on 127.0.0.1 only,
so nothing leaves this computer. It works the same whichever AI tool (or none) started it:

  GET  /                    the queue board, live from tracker/events
  GET  /cards               the review cards of --run, with an "Update queue" button added
  GET  /api/ping            {"ok": true}
  POST /api/drop            {"job": ID, "reason": "..."} -> one dropped event in tracker/events
  POST /api/update-queue    {"choices": {...}} -> saves the choices file in the run folder and runs
                            update-queue (import choices, save the run, queue Interested jobs)

It answers only requests addressed to 127.0.0.1 or localhost (a page on another site cannot reach it by
renaming itself), and saves only JSON sent from its own pages. If the port is busy it tries the next ten.

Saving writes files; it never commits or pushes. The agent (or the user) commits the new files,
as each button's message says. Build résumé stays an AI task: the page copies the request.
Python standard library only, plus tracker.py.
"""
import contextlib
import io
import json
import sys
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import tracker

# Added to a run's cards page when it is served: one button that sends the choices to the server.
CARDS_HOOK = """
<script>
(function(){
  const header = document.querySelector("header");
  if (!header || typeof choicesFile !== "function") return;
  const p = document.createElement("p");
  p.innerHTML = '<button id="uq" type="button">Update queue</button> ' +
    '<span class="note" id="uqnote">Saves your choices, saves this run and adds your Interested jobs to the queue board.</span>';
  header.append(p);
  document.getElementById("uq").addEventListener("click", async function(){
    const note = document.getElementById("uqnote"); this.disabled = true; note.textContent = "Saving…";
    try {
      const r = await fetch("/api/update-queue", {method: "POST", headers: {"Content-Type": "application/json"},
                                                 body: JSON.stringify({choices: JSON.parse(choicesFile())})});
      const j = await r.json();
      if (j.ok) { note.innerHTML = 'Queue updated: ' + j.message + ' <a href="/">Open the queue board</a>.'; }
      else { this.disabled = false; note.textContent = j.error; }
    } catch (e) { this.disabled = false; note.textContent = "The tracker server did not answer. Is tracker.py serve still running?"; }
  });
})();
</script>
"""


def run_folder(run):
    if not run:
        return None
    path = Path(run).expanduser().resolve()
    if not (path / "run.json").exists() or not (path / "cards.html").exists():
        sys.exit(f"{path} is not a finished search run (it needs run.json and cards.html)")
    return path


def quiet(fn, *a):
    """Run a tracker function; turn its exits into an error message and keep its output."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            result = fn(*a)
        return True, result, out.getvalue()
    except SystemExit as e:
        return False, None, str(e.code if e.code not in (None, 0) else out.getvalue()).strip()
    except Exception as e:  # report, never drop the connection
        return False, None, f"{type(e).__name__}: {e}"


def make_handler(run_dir, port):
    allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the terminal readable
            sys.stderr.write("tracker serve: " + fmt % args + "\n")

        def send(self, code, body, kind="text/html; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def reply(self, payload, code=200):
            self.send(code, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

        def local(self):
            """Refuse a request whose Host is not this computer (DNS rebinding)."""
            if (self.headers.get("Host") or "").lower() in hosts:
                return True
            self.send(421, "Refused: this server answers only http://127.0.0.1 or http://localhost.", "text/plain; charset=utf-8")
            return False

        def do_GET(self):
            if not self.local():
                return
            path = self.path.split("?", 1)[0]
            if path == "/":
                today = datetime.now(tracker.TZ).date()
                return self.send(200, tracker.render_board(tracker.load(), today, served=True))
            if path == "/cards":
                if not run_dir:
                    return self.send(404, "No search run was given. Start with: tracker.py serve --run RUN")
                page = (run_dir / "cards.html").read_text(encoding="utf-8")
                return self.send(200, page + CARDS_HOOK)
            if path == "/api/ping":
                return self.reply({"ok": True, "run": str(run_dir) if run_dir else None})
            self.send(404, "Not found")

        def do_POST(self):
            if not self.local():
                return
            # Only this page may save: refuse requests from other sites and non-JSON posts.
            origin = self.headers.get("Origin")
            if origin and origin not in allowed:
                return self.reply({"ok": False, "error": "Refused: request from another site."}, 403)
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self.reply({"ok": False, "error": "Refused: send JSON."}, 415)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            except ValueError:
                return self.reply({"ok": False, "error": "Refused: the request was not valid JSON."}, 400)
            path = self.path.split("?", 1)[0]
            if path == "/api/drop":
                return self.drop(body)
            if path == "/api/update-queue":
                return self.update_queue(body)
            self.reply({"ok": False, "error": "Not found"}, 404)

        def drop(self, body):
            job_id = str(body.get("job") or "")
            jobs = {e["id"]: e for e in tracker.load()["applications"]}
            job = jobs.get(job_id)
            if not job or tracker.status(job) != "queued":
                return self.reply({"ok": False, "error": "That job is not in the queue any more. Reload the board."}, 409)
            event = {"date": str(datetime.now(tracker.TZ).date()), "type": "dropped", "source": "user"}
            reason = str(body.get("reason") or "").strip()
            if reason:
                event["note"] = reason[:500]
            line = tracker.job_line(job_id, event)
            ok, _, message = quiet(tracker.commit, [line])
            if not ok:
                return self.reply({"ok": False, "error": message}, 400)
            self.reply({"ok": True, "file": f"tracker/events/{tracker.event_name(line)}"})

        def update_queue(self, body):
            if not run_dir:
                return self.reply({"ok": False, "error": "No search run was given to the server."}, 400)
            if run_dir.is_relative_to(tracker.RUNS.resolve()):
                return self.reply({"ok": False, "error": "This run is already saved, and its Interested jobs are "
                                   "already in the queue. Open the queue board instead."}, 409)
            choices = body.get("choices")
            if not isinstance(choices, dict) or not isinstance(choices.get("decisions"), dict):
                return self.reply({"ok": False, "error": "The choices were missing."}, 400)
            path = run_dir / f"decisions-{choices.get('run_id') or run_dir.name}.json"
            path.write_text(json.dumps(choices, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            ok, result, message = quiet(tracker.update_queue, run_dir, path)
            if not ok:
                return self.reply({"ok": False, "error": message}, 400)
            counts = result["counts"]
            self.reply({"ok": True, "saved": result["saved"],
                        "message": f"{counts.get('interested', 0)} interested, {counts.get('pass', 0)} passed; "
                                   f"run saved to {result['saved']}. Commit it and tracker/events/."})

    return Handler


def bind(port, run_dir, tries=10):
    """The server on the first free port from `port`; a clear message when none is free."""
    for p in range(port, port + tries):
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), make_handler(run_dir, p)), p
        except OSError:
            continue
    sys.exit(f"tracker serve: ports {port}-{port + tries - 1} are all in use. Stop the other server "
             "(an earlier tracker.py serve?) or pass --port N.")


def serve(port=8765, run=None, open_browser=True):
    run_dir = run_folder(run)
    server, port = bind(port, run_dir)
    url = f"http://127.0.0.1:{port}/"
    print(f"Queue board: {url}" + (f"\nReview cards: {url}cards" if run_dir else ""))
    print("Saving writes files only; commit them afterwards. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url + ("cards" if run_dir else ""))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
