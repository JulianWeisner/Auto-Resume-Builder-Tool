#!/usr/bin/env python3
"""Application tracker: every job from queue to final reply.

Each event is one file in tracker/events/; a job is the events that share its ID.
Status is derived from the dated events, never stored, so history and status cannot
drift, and branches that add events merge without conflicts.
See tracker/README.md for the schema and the rules.

Commands:
  tracker.py status [--all]                 Text view: one line per job, grouped by status
  tracker.py board [--fragment] [-o FILE]   The queue board as HTML (tracker/board.html by default;
                                            --fragment prints the body for drawing in a chat)
  tracker.py validate                       Check schema, links, hashes and archive coverage
  tracker.py add-archive applications/FOLDER  Record a newly archived application as applied
  tracker.py add-event ID|TEXT TYPE DATE [--source S] [--file F] [--gmail-id G] [--note N]
  tracker.py save-email MESSAGES.json [--log]
                                            Save Gmail connector messages to an archive's
                                            correspondence/ folder; print (and with --log,
                                            record) their events
  tracker.py update-queue RUN CHOICES.json  The user's "update queue": import their choices, export
                                            the queue, save the run under job-search/runs/ and add
                                            its Interested jobs to the tracker
  tracker.py import-queue QUEUE.json        Add a search run's "interested" jobs as queued
  (update-queue and import-queue need career informed search, which is not in this version yet.)

Dates are in this computer's local time zone. Set TRACKER_TZ to an IANA name
(for example America/Chicago) where the computer's zone is not yours, such as a cloud session.

Python 3.9+ and PyYAML (python3 tools/build_resume.py --setup installs it).
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # use the setup environment when it exists (build_resume.py --setup)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from resume_check import use_tool_env
    use_tool_env()
    sys.exit("tracker: PyYAML is missing. Run `python3 tools/build_resume.py --setup`, "
             "or `python3 -m pip install pyyaml`.")

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "tracker/events"
BOARD_PAGE = ROOT / "tracker/board.html"  # generated on request; ignored by Git
# The user's time zone: TRACKER_TZ when set, otherwise this computer's local zone (None).
if os.environ.get("TRACKER_TZ"):
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.environ["TRACKER_TZ"])
else:
    TZ = None
STALE_AFTER_DAYS = 21  # without search criteria, a posting is old after three weeks
SCHEMA_VERSION = 2
# Job details an event may carry. The latest event that sets one wins.
META_KEYS = ("company", "role", "posting_id", "posting_url", "search_run", "archive")

# Event types, in the order a job normally moves through them.
EVENT_TYPES = (
    "queued",        # chosen from a search run or pasted posting; nothing built yet
    "applied",       # the user confirmed submission (the archive is the evidence)
    "acknowledged",  # automated "we received your application"
    "screen",        # recruiter or hiring-manager call scheduled or held
    "assessment",    # take-home, case or test requested
    "interview",     # interview round scheduled or held
    "offer",
    "rejected",
    "withdrawn",     # the user withdrew a submitted application
    "dropped",       # the user chose not to pursue a queued job (Drop); note gives the reason
    "closed",        # no reply after the company's stated window, or posting removed
    "note",          # anything else worth keeping; never changes status
)
TERMINAL = {"offer", "rejected", "withdrawn", "closed", "dropped"}
ACTIVE = {"screen": "in process", "assessment": "in process", "interview": "in process"}
SOURCES = ("archive", "email", "search-run", "user")

# Status names in board order.
BOARD = ("queued", "applied", "acknowledged", "in process", "offer", "rejected", "withdrawn", "closed", "dropped")


# ---------------------------------------------------------------- event store
#
# Each event is its own file in tracker/events/, named by its date, type and a hash of its
# content. Two branches that add events add different files, so they merge without conflict
# anywhere, including GitHub's merge button. The same event added twice gets the same name and
# content, so it collapses to one file. Files are never edited; a correction is a new event.

def canonical(line):
    return json.dumps(line, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def event_name(line):
    digest = hashlib.sha256(canonical(line).encode()).hexdigest()[:12]
    return f"{line['date']}-{line['type']}-{digest}.json"


def read_lines(events=None):
    events = events or EVENTS
    return [(p.name, json.loads(p.read_text())) for p in sorted(events.glob("*.json"))]


def build(lines):
    """Group event lines into jobs. Details come from the events, latest first-set wins."""
    jobs = {}
    for name, line in sorted(lines, key=lambda nl: (event_order(nl[1]), nl[0])):
        job = jobs.setdefault(line["job"], {"id": line["job"], **{k: None for k in META_KEYS}, "events": []})
        for k in META_KEYS:
            if line.get(k):
                job[k] = line[k]
        job["events"].append({k: v for k, v in line.items() if k != "job"} | {"_file": name})
    apps = sorted(jobs.values(), key=lambda e: (first_date(e), e["id"]))
    return {"schema_version": SCHEMA_VERSION, "applications": apps}


def load(events=None):
    return build(read_lines(events))


def commit(new_lines, events=None):
    """Validate the store with the new events added, then write them. Returns the new model."""
    events = events or EVENTS
    lines = read_lines(events)
    names = {n for n, _ in lines}
    fresh = [(event_name(l), l) for l in new_lines if event_name(l) not in names]
    model = build(lines + fresh)
    errors = validate(model)
    if errors:
        sys.exit("not saved:\n" + "\n".join(errors))
    events.mkdir(parents=True, exist_ok=True)
    for name, line in fresh:
        (events / name).write_text(canonical(line) + "\n", encoding="utf-8")
    return model


def job_line(job_id, ev, **meta):
    return {"job": job_id, **{k: v for k, v in meta.items() if v}, **ev}


def event_order(ev):
    return (ev["date"], EVENT_TYPES.index(ev["type"]) if ev.get("type") in EVENT_TYPES else 99)


def first_date(entry):
    return min((ev["date"] for ev in entry["events"]), default="9999")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------- status

def status(entry):
    """Derive status from events. Terminal events win; then the furthest active step."""
    kinds = [ev["type"] for ev in sorted(entry["events"], key=event_order) if ev["type"] != "note"]
    terminal = [k for k in kinds if k in TERMINAL]
    if terminal:
        return terminal[-1]
    if any(k in ACTIVE for k in kinds):
        return "in process"
    for k in ("acknowledged", "applied", "queued"):
        if k in kinds:
            return k
    return "queued"


def last_activity(entry):
    return max((ev["date"] for ev in entry["events"]), default="")


def cmd_status(args):
    ledger = load()
    groups = {s: [] for s in BOARD}
    for e in ledger["applications"]:
        groups[status(e)].append(e)
    today = date.today()
    for s in BOARD:
        rows = groups[s]
        if not rows or (s == "queued" and not args.all and len(rows) > 20):
            if rows:
                print(f"\n{s.upper()} ({len(rows)}) — use --all to list")
            continue
        print(f"\n{s.upper()} ({len(rows)})")
        for e in sorted(rows, key=last_activity, reverse=True):
            applied = next((ev["date"] for ev in e["events"] if ev["type"] == "applied"), None)
            age = f"{(today - date.fromisoformat(applied)).days}d since applied" if applied else ""
            print(f"  {last_activity(e)}  {e['company']} · {e['role']}  {age}".rstrip())
    counts = {s: len(groups[s]) for s in BOARD if groups[s]}
    print("\n" + " · ".join(f"{k} {v}" for k, v in counts.items()))


# ----------------------------------------------------------------- validate

def archive_entries():
    """Every archived application folder (one per role) and its job-description metadata."""
    found = {}
    for jd in sorted((ROOT / "applications").rglob("job-description.md")):
        if "supporting" in jd.parts:
            continue
        text = jd.read_text()
        meta = yaml.safe_load(text.split("---\n")[1]) if text.startswith("---\n") else {}
        found[str(jd.parent.relative_to(ROOT))] = meta or {}
    return found


def validate(ledger):
    errors = []
    if ledger.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    ids, archives = set(), {}
    for e in ledger.get("applications", []):
        eid = e.get("id", "?")
        for field in ("id", "company", "role", "events"):
            if not e.get(field):
                errors.append(f"{eid}: missing {field}")
        if eid in ids:
            errors.append(f"{eid}: duplicate id")
        ids.add(eid)
        if e.get("archive"):
            if not (ROOT / e["archive"] / "job-description.md").exists():
                errors.append(f"{eid}: archive {e['archive']} has no job-description.md")
            archives[e["archive"]] = eid
        seen_gmail = set()
        for ev in e.get("events", []):
            where = f"{eid} {ev.get('date')} {ev.get('type')}"
            if ev.get("_file") and ev["_file"] != event_name(
                    {"job": eid, **{k: v for k, v in ev.items() if k != "_file"}}):
                errors.append(f"{where}: {ev['_file']} was edited after it was written; add a new event instead")
            if ev.get("type") not in EVENT_TYPES:
                errors.append(f"{where}: unknown event type")
            if ev.get("source") not in SOURCES:
                errors.append(f"{where}: source must be one of {', '.join(SOURCES)}")
            try:
                date.fromisoformat(ev.get("date", ""))
            except ValueError:
                errors.append(f"{where}: date must be YYYY-MM-DD")
            if ev.get("type") == "applied" and not e.get("archive"):
                errors.append(f"{where}: applied needs an archive (applications/README.md)")
            if ev.get("file"):
                p = ROOT / ev["file"]
                if not p.exists():
                    errors.append(f"{where}: missing file {ev['file']}")
                elif ev.get("sha256") and sha256(p) != ev["sha256"]:
                    errors.append(f"{where}: hash mismatch for {ev['file']}")
            gid = ev.get("gmail_message_id")
            if gid:
                if gid in seen_gmail:
                    errors.append(f"{where}: gmail message {gid} logged twice")
                seen_gmail.add(gid)
            if ev.get("source") == "email" and not (ev.get("file") and gid):
                errors.append(f"{where}: email events need the saved file and gmail_message_id")
        if e.get("archive") and not any(ev["type"] == "applied" for ev in e["events"]):
            errors.append(f"{eid}: archived but no applied event")
    for folder in archive_entries():
        if folder not in archives:
            errors.append(f"{folder}: archived application missing from the tracker")
    return errors


def cmd_validate(args):
    errors = validate(load())
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(1)
    print(f"OK: {len(load()['applications'])} jobs")


# --------------------------------------------------------------- add-event

def find(ledger, key):
    """An exact ID, or text that matches one entry's "company · role" (case-insensitive)."""
    apps = ledger["applications"]
    exact = [e for e in apps if e["id"] == key]
    if exact:
        return exact[0]
    k = key.lower()
    hits = [e for e in apps if k in f"{e['company']} · {e['role']}".lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"no tracker entry matches {key!r}")
    sys.exit(f"{key!r} matches {len(hits)} entries:\n" + "\n".join(f"  {e['id']}  {e['company']} · {e['role']}" for e in hits))


def cmd_add_event(args):
    ledger = load()
    entry = find(ledger, args.id)
    ev = {"date": args.date, "type": args.type, "source": args.source}
    for key, val in (("file", args.file), ("gmail_message_id", args.gmail_id), ("note", args.note)):
        if val:
            ev[key] = val
    if args.file:
        ev["sha256"] = sha256(ROOT / args.file)
    if args.gmail_id and any(x.get("gmail_message_id") == args.gmail_id for x in entry["events"]):
        sys.exit(f"gmail message {args.gmail_id} is already logged for {args.id}")
    model = commit([job_line(entry["id"], ev)])
    entry = next(e for e in model["applications"] if e["id"] == entry["id"])
    print(f"{entry['id']}: {status(entry)}")


# -------------------------------------------------------------- add-archive

def cmd_add_archive(args):
    """Record a newly archived application. A queued entry with the same posting ID becomes it."""
    ledger = load()
    folder = str((ROOT / args.folder).resolve().relative_to(ROOT))
    meta = archive_entries().get(folder)
    if meta is None:
        sys.exit(f"{folder} is not an archived application (no job-description.md)")
    if any(e.get("archive") == folder for e in ledger["applications"]):
        sys.exit(f"{folder} is already in the tracker")
    posting_id = meta.get("posting_id")
    queued = next((e for e in ledger["applications"]
                   if posting_id and e.get("posting_id") == posting_id and not e.get("archive")), None)
    job_id = queued["id"] if queued else folder.split("applications/", 1)[1]
    ev = {"date": str(meta["application_date"]), "type": "applied", "source": "archive",
          "file": f"{folder}/job-description.md", "note": "Submission confirmed by the user; see the archive"}
    line = job_line(job_id, ev, archive=folder, company=meta["company"], role=meta["role"],
                    posting_id=posting_id, posting_url=meta.get("posting_url"))
    model = commit([line])
    entry = next(e for e in model["applications"] if e["id"] == job_id)
    print(f"{job_id}: {status(entry)}" + (" (was queued)" if queued else ""))


# --------------------------------------------------------------- save-email

def local_date(iso_utc):
    return datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone(TZ)


def slug(address):
    return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")


def saved_gmail_ids(folder):
    ids = set()
    for p in folder.glob("*.txt"):
        m = re.search(r"^Gmail-Message-ID: (\S+)$", p.read_text(), re.M)
        if m:
            ids.add(m.group(1))
    return ids


def render_email(msg):
    sent = local_date(msg["date"])
    sender = f"{msg['senderName']} <{msg['sender']}>" if msg.get("senderName") else msg["sender"]
    head = [
        f"From: {sender}",
        f"To: {', '.join(msg.get('toRecipients', []))}",
        f"Date: {sent.isoformat()} ({msg['date']})",
        f"Subject: {msg['subject']}",
        f"Gmail-Message-ID: {msg['id']}",
        f"Gmail-Thread-ID: {msg.get('threadId', msg['id'])}",
        "Body: plain-text body as returned by the Gmail connector, unedited",
    ]
    return "\n".join(head) + "\n\n" + msg["plaintextBody"].rstrip("\n") + "\n"


def cmd_save_email(args):
    """Each message carries "archive" (the folder) and "kind" (an event type)."""
    messages = json.loads(Path(args.messages).read_text())
    events = []
    for msg in messages:
        folder = ROOT / msg["archive"] / "correspondence"
        folder.mkdir(parents=True, exist_ok=True)
        if msg["id"] in saved_gmail_ids(folder):
            print(f"skip {msg['id']}: already saved in {folder.relative_to(ROOT)}", file=sys.stderr)
            continue
        base = f"{local_date(msg['date']).date()}-{slug(msg['sender'])}"
        path, n = folder / f"{base}.txt", 2
        while path.exists():
            path, n = folder / f"{base}-{n}.txt", n + 1
        path.write_text(render_email(msg))
        ev = {"archive": msg["archive"], "date": str(local_date(msg["date"]).date()), "type": msg["kind"],
              "source": "email", "file": str(path.relative_to(ROOT)), "sha256": sha256(path),
              "gmail_message_id": msg["id"]}
        if msg.get("note"):
            ev["note"] = msg["note"]
        events.append(ev)
    if args.log and events:
        ledger, lines = load(), []
        for ev in events:
            targets = [e for e in ledger["applications"] if e.get("archive") and
                       (e["archive"] == ev["archive"] or e["archive"].startswith(ev["archive"] + "/"))]
            if not targets:
                sys.exit(f"no tracker entry for {ev['archive']}; files saved, nothing logged")
            lines += [job_line(e["id"], {k: v for k, v in ev.items() if k != "archive"}) for e in targets]
        commit(lines)
    print(json.dumps(events, indent=1, ensure_ascii=False))


# -------------------------------------------------------------------- board

LABEL_ORDER = {"Promising": 0, "Stretch": 1, "Deprioritize": 2}


def stale_after_days():
    """search.stale_after_days from the search criteria when they exist, otherwise three weeks."""
    path = ROOT / "career/search-criteria.yaml"
    if path.exists():
        criteria = yaml.safe_load(path.read_text()) or {}
        days = (criteria.get("search") or {}).get("stale_after_days")
        if days is not None:
            return int(days)
    return STALE_AFTER_DAYS


def queue_rows(ledger, today):
    """Queued jobs joined with their search-run cards, best fit first."""
    runs, rows = {}, []
    for e in ledger["applications"]:
        if status(e) != "queued":
            continue
        job = {}
        run = e.get("search_run")
        if run:
            if run not in runs:
                path = ROOT / "job-search/runs" / run / "application_queue.json"
                runs[run] = {j["job_id"]: j for j in json.loads(path.read_text())["jobs"]} if path.exists() else {}
            job = runs[run].get(e.get("posting_id"), {})
        screen, card = job.get("screening") or {}, job.get("card") or {}
        posted = job.get("posted_date")
        rows.append({
            "id": e["id"], "company": e["company"], "role": e["role"],
            "fit": screen.get("fit_percent"), "label": screen.get("label"),
            "age": (today - date.fromisoformat(posted)).days if posted else None,
            "business": card.get("business"), "owns": card.get("owns"),
            "details": " · ".join(x for x in (job.get("location"), job.get("workplace"),
                                              job.get("compensation") or "pay not posted") if x),
            "asks": [m if isinstance(m, str) else m.get("text", "") for m in (job.get("must_haves") or [])[:3]],
            "gap": screen.get("primary_gap"), "url": job.get("posting_url") or e.get("posting_url"),
        })
    rows.sort(key=lambda r: (LABEL_ORDER.get(r["label"], 3), -(r["fit"] or 0), r["company"]))
    return rows


BOARD_CSS = """
.tb{font-family:var(--font-sans,system-ui,-apple-system,"Segoe UI",sans-serif);color:var(--text-primary,#1f1f1d)}
.tb .stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:1.25rem}
.tb .stat{background:var(--bg-neutral,#f0eee8);border-radius:8px;padding:.75rem 1rem}
.tb .sl{font-size:13px;color:var(--text-secondary,#5f5e5a)} .tb .sn{font-size:24px;font-weight:500}
.tb .lh{display:flex;justify-content:space-between;font-size:13px;color:var(--text-secondary,#5f5e5a);margin:0 2px 8px}
.tb .list{max-height:var(--board-height,none);overflow-y:auto}
.tb .qc{background:var(--surface-2,#fff);border:.5px solid var(--border,#d3d1c7);border-radius:8px;margin-bottom:6px}
.tb .qc.open{border-color:var(--border-accent,#378add);box-shadow:0 0 0 1px var(--border-accent,#378add)}
.tb .hd{display:flex;align-items:center;gap:12px;padding:10px 14px;cursor:pointer}
.tb .rk{width:22px;font-size:13px;color:var(--text-muted,#888780);text-align:right;flex:none}
.tb .co{font-size:14px;font-weight:500;margin:0} .tb .ro{font-size:13px;color:var(--text-secondary,#5f5e5a);margin:1px 0 0}
.tb .fit{text-align:right;flex:none} .tb .fp{font-size:14px;font-weight:500} .tb .fl{font-size:11px;color:var(--text-muted,#888780)}
.tb .old{font-size:11px;font-weight:400;padding:2px 6px;border-radius:6px;margin-left:6px;background:var(--bg-warning,#faeeda);color:var(--text-warning,#854f0b)}
.tb .bd{display:none;padding:0 14px 14px 48px;font-size:13px;color:var(--text-secondary,#5f5e5a);line-height:1.55}
.tb .qc.open .bd{display:block} .tb .k{font-size:11px;color:var(--text-muted,#888780);margin:10px 0 2px}
.tb ul{margin:0;padding-left:18px} .tb .acts{display:flex;gap:8px;align-items:center;margin-top:12px}
.tb button{font:inherit;font-size:13px;padding:6px 12px;border-radius:8px;border:.5px solid var(--border-strong,#b4b2a9);background:transparent;color:inherit;cursor:pointer}
.tb button:hover{background:var(--surface-1,#f7f6f2)} .tb a{color:var(--text-accent,#185fa5)}
.tb .msg{font-size:12px;color:var(--text-muted,#888780)}
"""

BOARD_JS = """
(function(){const s=document.currentScript,b=(s&&s.parentElement)||document.querySelector('.tb');
b.addEventListener('click',function(e){
 const btn=e.target.closest('button');
 if(btn){const t=btn.dataset.a,m=btn.parentElement.querySelector('.msg');
  if(typeof sendPrompt==='function'){sendPrompt(t);return}
  (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(
   function(){m.textContent='Copied. Paste it into the chat with your assistant.'},
   function(){m.textContent='Tell your assistant: '+t});return}
 const h=e.target.closest('.hd');if(!h)return;const c=h.parentElement,was=c.classList.contains('open');
 b.querySelectorAll('.qc.open').forEach(function(x){x.classList.remove('open')});if(!was)c.classList.add('open')});
})();
"""


def days_ago(n):
    return "today" if n == 0 else "1 day ago" if n == 1 else f"{n} days ago"


def render_board(ledger, today, fragment=False):
    esc = html.escape
    rows, stale = queue_rows(ledger, today), stale_after_days()
    applied = sum(1 for e in ledger["applications"] if any(ev["type"] == "applied" for ev in e["events"]))
    cards = []
    for i, r in enumerate(rows, 1):
        name = f"{r['company']} · {r['role']}"
        old = f'<span class="old">posted {days_ago(r["age"])}</span>' if r["age"] is not None and r["age"] >= stale else ""
        fit = (f'<div class="fit"><div class="fp">{r["fit"]}%</div><div class="fl">{esc(r["label"] or "")}</div></div>'
               if r["fit"] is not None else "")
        body = []
        if r["business"]:
            body.append(f'<div style="color:var(--text-primary,#1f1f1d)">{esc(r["business"])}</div>')
        if r["owns"]:
            body.append(f'<div class="k">You\'d own</div><div>{esc(r["owns"])}</div>')
        if r["details"]:
            age = f' · posted {days_ago(r["age"])}' if r["age"] is not None else ""
            body.append(f'<div class="k">Details</div><div>{esc(r["details"])}{age}</div>')
        if r["asks"]:
            body.append('<div class="k">They ask most for</div><ul>' +
                        "".join(f"<li>{esc(a)}</li>" for a in r["asks"]) + "</ul>")
        if r["gap"]:
            body.append(f'<div class="k">Main gap</div><div>{esc(r["gap"])}</div>')
        link = f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">Posting</a>' if r["url"] else ""
        body.append(f'<div class="acts"><button data-a="{esc("Build a résumé for " + name)}">Build résumé</button>'
                    f'<button data-a="{esc("Drop " + name + " from the queue")}">Drop</button>{link}'
                    f'<span class="msg"></span></div>')
        cards.append(f'<div class="qc"><div class="hd"><span class="rk">{i}</span><div style="flex:1;min-width:0">'
                     f'<p class="co">{esc(r["company"])}{old}</p><p class="ro">{esc(r["role"])}</p></div>{fit}</div>'
                     f'<div class="bd">{"".join(body)}</div></div>')
    empty = ('<div class="msg" style="padding:8px 2px">The queue is empty. Run a search to fill it.</div>'
             if PIPELINE.exists() else
             '<div class="msg" style="padding:8px 2px">The queue is empty. Queued jobs will come from career '
             'informed search, which is not in this version of the tool yet.</div>')
    board = (f'<div class="tb"><style>{BOARD_CSS}</style>'
             f'<div class="stats"><div class="stat"><div class="sl">Applied</div><div class="sn">{applied}</div></div>'
             f'<div class="stat"><div class="sl">Queued</div><div class="sn">{len(rows)}</div></div></div>'
             f'<div class="lh"><span>Queue, best fit first</span><span>{len(rows)} jobs</span></div>'
             f'<div class="list">{"".join(cards) or empty}</div><script>{BOARD_JS}</script></div>')
    if fragment:
        return board
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Application tracker</title>"
            "<style>body{margin:0;padding:2rem 1rem;background:#faf9f5}.wrap{max-width:720px;margin:0 auto}"
            ".tb{--board-height:70vh}@media(prefers-color-scheme:dark){body{background:#1f1e1d}.tb{--text-primary:#f1efe8;"
            "--text-secondary:#b4b2a9;--text-muted:#888780;--surface-2:#2c2c2a;--surface-1:#262624;--bg-neutral:#2c2c2a;"
            "--border:#444441;--border-strong:#5f5e5a;--bg-warning:#633806;--text-warning:#fac775}}</style></head>"
            f"<body><div class=\"wrap\">{board}<p class=\"msg\" style=\"font:12px system-ui;color:#888780\">"
            f"Generated {today} from tracker/events by tools/tracker.py board.</p></div></body></html>\n")


def cmd_board(args):
    page = render_board(load(), datetime.now(TZ).date(), fragment=args.fragment)
    if args.fragment and not args.output:
        print(page)
        return
    out = Path(args.output) if args.output else BOARD_PAGE
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


# ------------------------------------------------------------- import-queue

def cmd_import_queue(args):
    ledger = load()
    queue = json.loads(Path(args.queue).read_text())
    run = queue["source"]["run_id"]
    by_posting = {e.get("posting_id"): e for e in ledger["applications"] if e.get("posting_id")}
    added = linked = 0
    lines, day = [], queue["source"]["run_date"]
    for job in queue["jobs"]:
        if job.get("decision") != "interested":
            continue
        entry = by_posting.get(job["job_id"])
        if entry:
            linked += 1
            if not any(x["type"] == "queued" for x in entry["events"]):
                lines.append(job_line(entry["id"], {"date": day, "type": "queued", "source": "search-run",
                                                    "note": f"Marked interested in search run {run}"},
                                      search_run=None if entry.get("search_run") else run))
            elif status(entry) == "queued" and entry.get("search_run") != run:
                # a queued job seen again takes the newer card
                lines.append(job_line(entry["id"], {"date": day, "type": "note", "source": "search-run",
                                                    "note": f"Marked interested again in search run {run}"},
                                      search_run=run))
            continue
        lines.append(job_line(job["job_id"], {"date": day, "type": "queued", "source": "search-run",
                                              "note": f"Marked interested in search run {run}"},
                              company=job["company"], role=job["title"], posting_id=job["job_id"],
                              posting_url=job.get("posting_url"), search_run=run))
        added += 1
    commit(lines)
    print(f"{run}: {added} queued, {linked} linked to existing entries")


# ------------------------------------------------------------- update-queue

PIPELINE = ROOT / "job-search/tools/pipeline.py"
RUN_INPUTS = {"searches", "details"}  # host-saved inputs; their originals are archived under raw/


def cmd_update_queue(args):
    """The user's "update queue": import choices, export, save the run, add Interested jobs to the tracker."""
    import shutil
    import subprocess

    if not PIPELINE.exists():
        sys.exit("update-queue needs career informed search (job-search/), which is not in this version of the tool yet")

    run_dir, choices = Path(args.run).resolve(), Path(args.choices).resolve()
    run_json = run_dir / "run.json"
    if not run_json.exists():
        sys.exit(f"{run_dir} has no run.json; finish the run (assemble, validate, cards) first")
    run_id = json.loads(run_json.read_text())["run_id"]
    saved = ROOT / "job-search/runs" / run_id
    if saved.exists() and saved.resolve() != run_dir:
        sys.exit(f"{saved.relative_to(ROOT)} already exists; a saved run is never overwritten")

    def pipeline(*a):
        out = subprocess.run([sys.executable, str(PIPELINE), *a], capture_output=True, text=True)
        if out.returncode:
            sys.exit(f"pipeline.py {a[0]} failed:\n{out.stderr or out.stdout}")
        if out.stderr:
            print(out.stderr.strip(), file=sys.stderr)
        return out.stdout

    decided = json.loads(pipeline("decide", str(run_json), str(choices)))
    queue_path = run_dir / "application_queue.json"
    queue_path.write_text(pipeline("export", str(run_json), "--artifacts", str(run_dir / "artifacts")), encoding="utf-8")
    if not json.loads(queue_path.read_text()).get("choices_imported"):
        sys.exit("export reports no choices imported; nothing saved")
    if saved.resolve() != run_dir:
        shutil.copytree(run_dir, saved, ignore=lambda d, names: [n for n in names if Path(d) == run_dir and n in RUN_INPUTS])
    args.queue = str(saved / "application_queue.json")
    cmd_import_queue(args)
    print(f"choices: {decided['counts']}")
    print("commit: " + " ".join(str(p.relative_to(ROOT)) for p in (saved, EVENTS)))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--all", action="store_true"); s.set_defaults(fn=cmd_status)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    s = sub.add_parser("board"); s.add_argument("--fragment", action="store_true"); s.add_argument("-o", "--output")
    s.set_defaults(fn=cmd_board)
    s = sub.add_parser("add-event")
    s.add_argument("id", help="tracker ID, or text matching one job's company and role")
    s.add_argument("type", choices=EVENT_TYPES); s.add_argument("date")
    s.add_argument("--source", choices=SOURCES, default="user")
    s.add_argument("--file"); s.add_argument("--gmail-id"); s.add_argument("--note")
    s.set_defaults(fn=cmd_add_event)
    s = sub.add_parser("add-archive"); s.add_argument("folder"); s.set_defaults(fn=cmd_add_archive)
    s = sub.add_parser("save-email"); s.add_argument("messages")
    s.add_argument("--log", action="store_true", help="also record the events in the tracker")
    s.set_defaults(fn=cmd_save_email)
    s = sub.add_parser("update-queue", help="import choices, save the run and queue its Interested jobs")
    s.add_argument("run"); s.add_argument("choices"); s.set_defaults(fn=cmd_update_queue)
    s = sub.add_parser("import-queue"); s.add_argument("queue"); s.set_defaults(fn=cmd_import_queue)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
