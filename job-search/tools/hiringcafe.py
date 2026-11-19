#!/usr/bin/env python3
"""L0 intake for HiringCafe: save connector responses without retyping, deduplicate, ingest and
write the jobs.json that `pipeline.py screen` reads.

Connector output exists only in the agent's session transcript, so this reads that transcript
(a Claude Code JSONL file) and copies every get_job_details result verbatim.

  hiringcafe.py searches <transcript.jsonl | responses dir> <run_dir>   after searching: write search_log.json
  hiringcafe.py extract <transcript.jsonl> <run_dir>
  hiringcafe.py ingest-raw <raw_dir> <run_dir>    rebuild from saved raw/hiringcafe/*.md (frozen sets)

Writes into run_dir:
  raw/hiringcafe/<job_id>.md     each response as received (sha256 recorded)
  artifacts/<artifact_id>/       B5 JD artifact of the "Full description" section
  jobs.json                      one entry per unique job: id, company, title, posting_url, location,
                                 workplace, compensation, posted_date, jd_artifact, aliases, and
                                 deadline / travel_percent when the description states them
Extracted deadlines and travel carry the matched text in `extracted` so the agent can confirm them.
When run_dir holds plan.json (pipeline.py plan), extract also writes search_log.json from the
search_jobs calls in the transcript: each planned search found there is logged as run, with its result
count and job IDs; planned searches not found stay unlogged (status reports them); searches outside the
plan are listed under "extra". Each job in jobs.json records found_by: the plan searches that returned it.
Prints counts. A description that ends with the provider truncation marker is ingested as truncated
(L1 makes it evaluation_error); any other description is asserted complete.
Needs nothing beyond the standard library and jd_ingest.py."""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jd_ingest  # noqa: E402
import intake  # noqa: E402

TOOL = "get_job_details"  # connector tool names vary (server name or ID prefix); match the suffix
FIELDS = {"Location": "location", "Workplace": "workplace", "Compensation": "compensation", "Posted": "posted_date",
          "Job ID": "provider_job_id", "Seniority": "seniority"}


def tool_results(transcript, suffix):
    """(input, text, timestamp) for each successful call of a tool whose name ends with suffix."""
    calls, out = {}, []
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            suffixes = (suffix, "search_hiringcafe_jobs") if suffix == "search_jobs" else (suffix, "get_hiringcafe_job_details")
            if block.get("type") == "tool_use" and block.get("name", "").endswith(suffixes):
                calls[block["id"]] = block.get("input") or {}
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in calls and not block.get("is_error"):
                parts = block.get("content")
                text = parts if isinstance(parts, str) else "".join(p.get("text", "") for p in parts or [])
                out.append((calls[block["tool_use_id"]], text, entry.get("timestamp")))
    return out


def search_key(text, workplace=None, industries=None):
    return (" ".join((text or "").casefold().split()), "remote" if workplace and "remote" in str(workplace).casefold() else "",
            tuple(sorted(industries or [])))


def parse_search(text):
    """Result items from one search response: job_id, title, company, posted_date, url."""
    return intake.search(text)["items"]


def search_log(found, plan_doc, existing=None):
    """search_log.json from search responses, matched to the plan by query text, remote workplace and industry
    filter. found: (input, text) pairs. Each run search records its result items (job_id, title, company,
    posted_date, url), which pipeline.py candidates selects from. Keeps an agent's 'skipped' entries."""
    planned = {search_key(x["text"], x.get("workplace"), x.get("industries")): x["id"] for x in plan_doc["searches"]}
    by_id = {x["id"]: x["id"] for x in plan_doc["searches"]}
    logged, extra = {}, []
    for inp, text in found:
        sid = inp.get("plan_id") if inp.get("plan_id") in by_id else \
            planned.get(search_key(inp.get("search"), inp.get("workplace_types"), inp.get("industries")))
        try:
            receipt = intake.search(text)
            items = receipt["items"]
        except (intake.IntakeError, TypeError, AttributeError) as e:
            failure = {"id": sid, "status": "unresolved", "results": 0, "items": [], "reason": str(e),
                       "response_sha256": inp.get("_response_sha256"),
                       "request": {k: v for k, v in inp.items() if not k.startswith("_")}}
            if sid:
                # Never overwrite an earlier failure with a later success: the run
                # must account for every response, including a malformed page.
                prev = logged.setdefault(sid, failure)
                prev["status"] = "unresolved"
                prev.setdefault("errors", []).append(str(e))
            else:
                extra.append(failure)
            continue
        if sid:
            prev = logged.setdefault(sid, {"id": sid, "status": "run", "results": 0, "items": []})
            seen = {i["job_id"] for i in prev["items"]}
            prev["items"] += [i for i in items if i["job_id"] not in seen]  # a second page merges
            prev["results"] = len(prev["items"])
            query = next(x for x in plan_doc["searches"] if x["id"] == sid)
            prev.setdefault("receipts", []).append({"format": receipt["format"],
                "response_sha256": inp.get("_response_sha256"),
                "reported_count": receipt["reported_count"], "request": inp,
                "returned": receipt["returned"],
                "filter_checks": intake.filter_checks(query.get("requested_filters", {"search": query["text"]}), receipt["returned"])})
        else:
            extra.append({"query": inp, "results": len(items), "items": items})
    for e in (existing or {}).get("searches", []):
        if e.get("id") not in logged and e.get("status") == "skipped":
            logged[e["id"]] = e
    order = [x["id"] for x in plan_doc["searches"]]
    return {"searches": [logged[i] for i in order if i in logged], "extra": extra}


def search_responses(source):
    """(input, text) pairs from a session transcript, or from a directory of saved responses named
    <plan id>.md (for AI products without a readable transcript: save each response's text under its plan id)."""
    src = Path(source)
    if src.is_dir():
        found = []
        for f in sorted(src.iterdir()):
            if f.suffix not in {".md", ".json", ".txt"}:
                continue
            try:
                text = f.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                text = "UNREADABLE UTF-8 RESPONSE"  # raw bytes are archived before parsing
            inp = {"plan_id": f.stem.replace("__", ":"), "_source_path": str(f)}
            if f.suffix == ".json":
                try:
                    envelope = json.loads(text)
                    if isinstance(envelope, dict) and "response" in envelope and isinstance(envelope.get("request", {}), dict):
                        inp.update(envelope.get("request") or {})
                        inp["plan_id"] = envelope.get("plan_id", inp["plan_id"])
                        text = envelope["response"]
                except json.JSONDecodeError:
                    pass  # adapter records the unsupported input, not an empty search
            inp["_source_path"] = str(f)  # request metadata cannot redirect original-source retention
            found.append((inp, text))
        return found
    return [(inp, text) for inp, text, _ in tool_results(src, "search_jobs")]


def write_search_log(source, run_dir):
    run_dir = Path(run_dir)
    plan_doc = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    log_path = run_dir / "search_log.json"
    existing = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else None
    found = search_responses(source)
    raw = run_dir / "raw" / "searches"
    raw.mkdir(parents=True, exist_ok=True)
    for i, (inp, value) in enumerate(found):
        data = Path(inp["_source_path"]).read_bytes() if inp.get("_source_path") else \
            (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)).encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        (raw / f"{digest}.response").write_bytes(data)
        inp["_response_sha256"] = digest
    log = search_log(found, plan_doc, existing)
    log_path.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"searches_planned": len(plan_doc["searches"]),
            "searches_logged": sum(e["status"] == "run" for e in log["searches"]),
            "searches_extra": len(log["extra"]), "results": sum(e.get("results", 0) for e in log["searches"]),
            "unresolved": sum(e["status"] == "unresolved" for e in log["searches"])}


def responses(transcript):
    """(job_id, text, timestamp) for each get_job_details result, in transcript order."""
    return [(inp.get("job_id"), text, ts) for inp, text, ts in tool_results(transcript, TOOL)]


def parse(text):
    """Metadata and description from one response."""
    value = intake.unpack(text)
    if isinstance(value, dict):
        return intake.detail(value)
    text = value
    head = re.match(r"# \[(?P<title>.+?)\]\((?P<url>[^)]+)\)\n\*\*(?P<company>.+?)\*\*", text)
    if not head:
        raise ValueError("response does not start with the job header")
    job = {"title": head["title"], "posting_url": head["url"], "company": head["company"]}
    for label, value in re.findall(r"^- \*\*(.+?):\*\* (.*)$", text.split("\n## ", 1)[0], re.M):
        if label in FIELDS:
            job[FIELDS[label]] = value.strip()
    parts = text.split("\n## Full description\n", 1)
    if len(parts) != 2:
        raise ValueError("response has no Full description section")
    if "posted_date" in job:
        job["posted_date"] = intake.date(job["posted_date"])
    return job, parts[1]


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DEADLINE_RE = re.compile(r"(?:application (?:close|closing|end) date|job posting end date|(?:job )?posting will close(?: on)?|apply by|applications? (?:are )?"
                         r"(?:due|accepted until|close[sd]?(?: on)?)|application deadline(?: for this job)?(?: is)?)"
                         r"[^\n\d]{0,12}?\b(?P<date>\d{4}-\d\d-\d\d|\d{1,2}[/-]\d{1,2}[/-]\d{4}|[A-Z][a-z]{2,8}\.? \d{1,2},? \d{4})", re.I)
TRAVEL_RE = re.compile(r"(?:travel[^.\n%]{0,40}?(?P<a>\d{1,3})\s?%|(?P<b>\d{1,3})\s?%[^.\n]{0,20}?travel)", re.I)


def to_date(text):
    """ISO date from 2026-12-31, 12/31/2026, 12-31-2026 or December 31, 2026; None if unreadable."""
    try:
        if re.fullmatch(r"\d{4}-\d\d-\d\d", text):
            return datetime.date.fromisoformat(text).isoformat()
        m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
        if m:
            return datetime.date(int(m[3]), int(m[1]), int(m[2])).isoformat()
        m = re.fullmatch(r"([A-Za-z]{3})[a-z]*\.? (\d{1,2}),? (\d{4})", text)
        if m and m[1].lower() in MONTHS:
            return datetime.date(int(m[3]), MONTHS[m[1].lower()], int(m[2])).isoformat()
    except ValueError:
        return None
    return None


def stated_terms(description):
    """Deadline and travel percentage stated in the description, with the matched text for confirmation.
    Travel takes the highest percentage mentioned with the word travel."""
    out, extracted = {}, {}
    m = DEADLINE_RE.search(description)
    if m and to_date(m["date"]):
        out["deadline"], extracted["deadline"] = to_date(m["date"]), m.group(0).strip()
    travel = [(int(t.group("a") or t.group("b")), t.group(0).strip()) for t in TRAVEL_RE.finditer(description)]
    travel = [t for t in travel if t[0] <= 100]
    if travel:
        out["travel_percent"], extracted["travel_percent"] = max(travel)
    if extracted:
        out["extracted"] = extracted
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def extract(transcript, run_dir):
    run_dir = Path(run_dir)
    result = process(responses(transcript), run_dir)
    if (run_dir / "plan.json").exists():
        if not (run_dir / "search_log.json").exists():
            result.update(write_search_log(transcript, run_dir))
        log = json.loads((run_dir / "search_log.json").read_text(encoding="utf-8"))
        doc = json.loads((run_dir / "jobs.json").read_text(encoding="utf-8"))
        for j in doc["jobs"]:
            j["found_by"] = [e["id"] for e in log["searches"]
                             if ({j["provider_job_id"]} | {a.split(":", 1)[-1] for a in j.get("aliases", [])})
                             & {i["job_id"] for i in e.get("items", [])}]
        (run_dir / "jobs.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def raw_responses(raw_dir):
    """Saved responses as (job_id, text, None), in file-name order."""
    return [(p.stem, p.read_bytes(), None) for p in sorted(Path(raw_dir).iterdir())
            if p.suffix in {".md", ".json", ".txt"}]


def process(found, run_dir):
    run_dir = Path(run_dir)
    raw_dir, art_dir = run_dir / "raw" / "hiringcafe", run_dir / "artifacts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    art_dir.mkdir(parents=True, exist_ok=True)
    jobs, by_pid, by_key, problems = [], {}, {}, []
    for pid, text, ts in found:
        data = text if isinstance(text, bytes) else text.encode("utf-8") if isinstance(text, str) else json.dumps(text, ensure_ascii=False).encode("utf-8")
        # Preserve even unknown/error/duplicate responses before interpreting them.
        digest = hashlib.sha256(data).hexdigest()
        (raw_dir / f"response-{digest}.original").write_bytes(data)
        try:
            if isinstance(text, bytes):
                text = text.decode("utf-8")
            job, description = parse(text)
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", str(job.get("provider_job_id") or pid or "")):
                raise ValueError("invalid job ID for intake")
            if pid and job.get("provider_job_id") and pid != job["provider_job_id"]:
                raise ValueError("requested job ID differs from returned ID")
        except (ValueError, TypeError, AttributeError) as e:
            problems.append(f"{pid}: {e}")
            continue
        pid = job.get("provider_job_id") or pid
        if pid in by_pid:  # the same job fetched twice: keep the first response
            if by_pid[pid]["jd_artifact"]["canonical_sha256"] != hashlib.sha256(description.encode("utf-8")).hexdigest():
                problems.append(f"{pid}: conflicting repeated detail response; original sources retained")
            continue
        key = (norm(job["company"]), norm(job["title"]), tuple(sorted(norm(job.get("location")).split(" or "))),
               hashlib.sha256(re.sub(r"\s+", " ", description).strip().encode("utf-8")).hexdigest())
        if key in by_key:  # a repost under another provider ID
            by_key[key].setdefault("aliases", []).append(f"hiringcafe:{pid}")
            by_pid[pid] = by_key[key]
            continue
        suffix = ".md" if isinstance(intake.unpack(text), str) else ".json"
        (raw_dir / f"{pid}{suffix}").write_bytes(data)
        prov = {"provider_job_id": pid, "url": job["posting_url"], "response_sha256": hashlib.sha256(data).hexdigest(),
                "retrieval_tool": "HiringCafe get_job_details", "representation": "Full description section of the response",
                "company": job["company"], "title": job["title"]}
        if ts:
            prov["retrieved_at"] = ts
        complete = None if jd_ingest.detect_marker(description) else "complete"
        try:
            artifact, normalized = jd_ingest.ingest(description, "hiringcafe", prov, completeness=complete)
        except jd_ingest.IngestError as e:
            problems.append(f"{pid}: ingest failed: {e.code}: {e}")
            continue
        jd_ingest.write_artifact(art_dir / artifact["artifact_id"], artifact, normalized)
        job.pop("provider_job_id", None)
        entry = {"id": f"hiringcafe:{pid}", "provider": "hiringcafe", "provider_job_id": pid, **job,
                 "jd_artifact": {"artifact_id": artifact["artifact_id"], "canonical_sha256": artifact["canonical"]["sha256"]},
                 "completeness": artifact["source"]["completeness"]["status"], **stated_terms(description)}
        jobs.append(entry)
        by_pid[pid], by_key[key] = entry, entry
    if (run_dir / "search_log.json").exists():
        log = json.loads((run_dir / "search_log.json").read_text(encoding="utf-8"))
        for job in jobs:
            pids = {job["provider_job_id"]} | {a.split(":", 1)[-1] for a in job.get("aliases", [])}
            job["found_by"] = [e["id"] for e in log.get("searches", [])
                               if pids & {x["job_id"] for x in e.get("items", [])}]
    duplicates = len(found) - len(jobs) - len(problems)
    (run_dir / "jobs.json").write_text(json.dumps({"discovered": len(jobs) + duplicates, "duplicates": duplicates,
                                                   "jobs": jobs, "intake_errors": problems}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"responses": len(found), "unique": len(jobs), "duplicates": duplicates,
            "truncated": sum(j["completeness"] == "truncated" for j in jobs),
            "insufficient": sum(j["completeness"] == "insufficient" for j in jobs), "problems": problems}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] not in {"extract", "ingest-raw", "searches"}:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    if args[0] == "searches":
        result = write_search_log(args[1], args[2])
        print(json.dumps(result, indent=1))
        return 0 if result["searches_logged"] and not result["unresolved"] else 1
    result = extract(args[1], args[2]) if args[0] == "extract" else process(raw_responses(args[1]), args[2])
    if not result["responses"]:
        result["problems"].append("no HiringCafe get_job_details responses found in the transcript")
    print(json.dumps(result, indent=1))
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

