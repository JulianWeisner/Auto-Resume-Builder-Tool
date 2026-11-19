#!/usr/bin/env python3
"""Deterministic search-run validation, screening helpers and summaries.

validate, summarize and review use the Python standard library only. screen and
check-profile read YAML and need PyYAML (python3 tools/build_resume.py --setup).
Runs use schema 1.3: L1 hard gates (screen), L2 knockout routing (job.screen), L3 full scoring,
posting dates and the job-first card object; `cards` renders the review page. Every fit comes from
the shared engine in tools/evaluation.py (shared-2). Earlier schema versions and fit formulas were
removed on 2026-11-17; Git history keeps them. See job-search/README.md."""
import datetime
import math
import html
import hashlib
import json
import re
import sys
from pathlib import Path

STATUSES = {"eligible", "excluded", "needs_verification", "evaluation_error", "deprioritized"}
ROUTINGS = {"full_score", "full_score_flagged", "deprioritized"}
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
import evaluation
import conditions as shared_conditions
CAREER_REPO = evaluation.career_repo()  # ARB_CAREER_REPO points it at another career folder (the tests use the sample person)
DEFAULT_PROFILE = CAREER_REPO / "career" / "capability-profile.yaml"
DEFAULT_CRITERIA = CAREER_REPO / "career" / "search-criteria.yaml"
SCHEMA_VERSION = "1.3"
DATE = re.compile(r"\d{4}-\d\d-\d\d")
CARD_TEXT = ("business", "industry", "size", "owns", "level", "reports_to", "team")
DECISIONS = {"undecided", "pass", "interested"}
KINDS = {"do", "want", "nice", "role", "about", "trait", "condition"}
CONFIDENCE = {"high", "medium", "low"}
ELIGIBILITY = {"pass", "unresolved", "fail"}
ALIGNMENT = {"direct", "transferable", "adjacent", "none"}
RESULT_QUALITY = {"established", "unclear", "none"}
QUOTE_STATUS = {"unverified", "source_verified"}


def load_jd_artifact(artifacts_dir, artifact_id, cache):
    """Load and revalidate a B5 JD artifact from artifacts_dir/<artifact_id>/ (see jd_ingest.py)."""
    if artifact_id not in cache:
        import jd_ingest
        directory = Path(artifacts_dir) / artifact_id
        artifact, normalized, errors = jd_ingest.validate_dir(directory)
        canonical = jd_ingest.reconstruct(artifact, normalized)[0] if not errors else None
        cache[artifact_id] = (artifact, canonical, [e["code"] + ": " + e["message"] for e in errors])
    return cache[artifact_id]


def check_source_quote(job, r, prefix, artifacts_dir, cache):
    """Errors for one requirement that claims a source-verified quote."""
    ref, art = r.get("source"), job.get("jd_artifact")
    if not isinstance(ref, dict) or not isinstance(art, dict) or not art.get("artifact_id"):
        return [f"{prefix}: source_verified quote needs requirement source and job jd_artifact"]
    if artifacts_dir is None:
        return [f"{prefix}: source_verified quote cannot be verified without --artifacts"]
    artifact, canonical, errors = load_jd_artifact(artifacts_dir, art["artifact_id"], cache)
    if errors:
        return [f"{prefix}: JD artifact {art['artifact_id']} invalid: {e}" for e in errors]
    if artifact.get("artifact_id") != art["artifact_id"] or \
            artifact["canonical"]["sha256"] != art.get("canonical_sha256"):
        return [f"{prefix}: jd_artifact identity or canonical_sha256 does not match the artifact"]
    import jd_ingest
    return [f"{prefix}: {e}" for e in jd_ingest.verify_quote(artifact, canonical, ref, r.get("quote"))]


def loose(text):
    """Text for a tolerant quote check: non-breaking spaces, curly quotes and runs of whitespace are folded."""
    text = re.sub(r"[\u00a0\u2007\u202f\ufeff]", " ", text or "")
    text = text.translate(str.maketrans("\u2018\u2019\u201c\u201d\u2013\u2014", "''\"\"--"))
    return re.sub(r"\s+", " ", text).strip()


def quote_warnings(run, artifacts_dir):
    """Unverified quotes from the description that do not appear in the job's JD artifact, even loosely.
    Quotes taken from provider metadata (source_span.source other than description) are skipped."""
    cache, out = {}, []
    for j in run.get("jobs", []):
        art = j.get("jd_artifact")
        if not isinstance(art, dict) or not art.get("artifact_id"):
            continue
        _, canonical, errs = load_jd_artifact(artifacts_dir, art["artifact_id"], cache)
        if errs or canonical is None:
            continue
        body = loose(canonical)
        for q in (j.get("card") or {}).get("responsibilities") or []:
            if loose(q) not in body:
                out.append(f"{j['id']} card: responsibility quote not found in the posting text: {q[:60]}")
        for r in j.get("requirements", []):
            span = r.get("source_span") or {}
            if r.get("quote_status", "unverified") == "unverified" and span.get("source", "description") == "description" \
                    and loose(r.get("quote")) not in body:
                out.append(f"{j['id']} {r.get('tag')}: quote not found in the posting text")
    return out


def fit(requirements):
    """Final fit for scored requirements through the shared engine (tools/evaluation.py, current policy).
    None when there is nothing to score or an ask is unscored."""
    asks = [r for r in requirements if r["kind"] != "condition"]
    if not asks or any(r.get("score") is None for r in asks):
        return None
    return evaluation.assess(requirements)["functional_fit"]


def must_haves(job, n=3):
    """The asks a card shows as 'what they ask for most': defining first, then mandatory, in posting order."""
    asks = [r for r in job.get("requirements", []) if r.get("kind") != "condition" and r.get("mandatory") is True]
    return [r["quote"] for r in sorted(asks, key=lambda r: not r.get("defining"))[:n]]


def critical_gaps(requirements):
    """Mandatory asks scored 0-1 or contradicted by dated records (qualification_status unmet)."""
    return [r.get("competency_id") for r in requirements
            if r.get("kind") != "condition" and r.get("mandatory") is True
            and (r.get("score", 4) <= 1 or r.get("qualification_status") == "unmet")]


def routing(requirements):
    """L2 rule: 0 gaps -> full_score; 1 non-defining gap -> full_score_flagged;
    2+ gaps or any gap on a defining ask -> deprioritized."""
    gaps = critical_gaps(requirements)
    defining = {r.get("competency_id") for r in requirements if r.get("defining") is True}
    if len(gaps) >= 2 or defining & set(gaps):
        return "deprioritized"
    return "full_score_flagged" if gaps else "full_score"

def validate(run, artifacts_dir=None, known_ids=None):
    """Structural checks; with artifacts_dir, also verify source_verified quotes against B5 artifacts;
    with known_ids (career_ids()), also require every cited record ID to exist in the career records."""
    errors = []
    artifact_cache = {}
    def check(ok, msg):
        if not ok:
            errors.append(msg)
    version = run.get("schema_version")
    if run.get("workflow_version") == 2:
        check(isinstance(run.get("l1_rules"), dict), "current run must pin L1 rules")
    check(version == SCHEMA_VERSION, f"schema_version must be {SCHEMA_VERSION}")
    check(bool(DATE.fullmatch(str(run.get("run_date", "")))), "run needs run_date (YYYY-MM-DD)")
    check(bool(re.fullmatch(r"[a-f0-9]{40}", str(run.get("source_commit", "")))), "source_commit must be a pinned 40-character SHA")
    jobs = run.get("jobs", [])
    check(isinstance(jobs, list), "jobs must be an array")
    if not isinstance(jobs, list):
        return errors
    check(run.get("discovered_count", -1) == len(jobs) + run.get("duplicate_count", 0),
          "discovered_count must equal unique jobs plus duplicates")
    seen = set()
    for i, j in enumerate(jobs):
        prefix = f"jobs[{i}]"
        if run.get("workflow_version") == 2:
            if artifacts_dir is None:
                errors.append(f"{prefix}: current run needs --artifacts for L1 verification")
            else:
                errors.extend(enforce_l1(j, j, run, artifacts_dir))
        jid = j.get("id")
        check(bool(jid) and jid not in seen, f"{prefix}: missing or duplicate ID")
        seen.add(jid)
        for k in ("provider", "company", "title", "posting_url"):
            check(bool(j.get(k)), f"{prefix}: missing {k}")
        status = j.get("status")
        check(status in STATUSES, f"{prefix}: invalid status")
        check(j.get("decision") in DECISIONS, f"{prefix}: invalid decision")
        requirements = j.get("requirements", [])
        policy = j.get("evaluation_policy")
        shared = policy in evaluation.POLICIES
        if run.get("evaluation_policy") in evaluation.POLICIES:
            check(policy == run.get("evaluation_policy"), f"{prefix}: shared evaluation policy missing or differs from the run")
        check(isinstance(requirements, list), f"{prefix}: requirements must be array")
        if not isinstance(requirements, list):
            continue
        tags = set()
        competencies = set()
        for r in requirements:
            if run.get("workflow_version") == 2 and r.get("mandatory"):
                check(r.get("mandatory_basis") == "explicit" and r.get("kind") != "do",
                      f"{prefix}: mandatory asks need explicit posting basis; responsibilities stay inferred concerns")
            tag = r.get("tag")
            check(bool(tag) and tag not in tags, f"{prefix}: duplicate/missing tag")
            tags.add(tag)
            check(bool(r.get("quote")), f"{prefix}: missing verbatim requirement quote")
            quote_status = r.get("quote_status", "unverified")
            check(quote_status in QUOTE_STATUS, f"{prefix}: invalid quote_status")
            if quote_status == "source_verified":
                errors.extend(check_source_quote(j, r, f"{prefix} {tag}", artifacts_dir, artifact_cache))
            kind = r.get("kind")
            check(kind in KINDS, f"{prefix}: invalid requirement kind")
            if kind == "condition":
                check(r.get("condition_status") in {"pass", "fail", "unknown"}, f"{prefix}: invalid condition")
                check(r.get("score") is None, f"{prefix}: conditions are not scored")
            else:
                check(type(r.get("score")) is int and 0 <= r["score"] <= 4, f"{prefix}: missing/invalid ask score")
            check(isinstance(r.get("record_ids"), list), f"{prefix}: missing record_ids")
            if known_ids is not None and isinstance(r.get("record_ids"), list):
                for rid in r["record_ids"]:
                    check(rid in known_ids, f"{prefix} {tag}: record {rid} does not exist in the career records")
            if kind != "condition":
                cid = r.get("competency_id")
                check(isinstance(cid, str) and bool(cid.strip()),
                      f"{prefix}: ask missing competency_id")
                if cid:
                    check(cid not in competencies, f"{prefix}: duplicate competency_id {cid}")
                    competencies.add(cid)
                check(type(r.get("mandatory")) is bool,
                      f"{prefix}: ask requires explicit mandatory boolean")
                check(bool(r.get("evidence_note")), f"{prefix}: missing evidence_note")
                alignment = r.get("evidence_alignment")
                result = r.get("result_quality")
                check(alignment in ALIGNMENT, f"{prefix}: invalid evidence_alignment")
                check(result in RESULT_QUALITY, f"{prefix}: invalid result_quality")
                score = r.get("score")
                if type(score) is int:
                    if score == 0:
                        check(alignment == "none", f"{prefix}: zero score requires none alignment")
                    if score >= 3:
                        check(alignment in {"direct", "transferable"},
                              f"{prefix}: score >=3 needs direct or transferable evidence")
                    if score == 4:
                        check(result == "established", f"{prefix}: score 4 needs established result")
                    if score > 0:
                        check(bool(r.get("record_ids")), f"{prefix}: scored evidence missing record_ids")
                if r.get("mandatory"):
                    check(r.get("qualification_status") in {"supported", "unresolved", "unmet"},
                          f"{prefix}: mandatory ask needs qualification_status")
                qs = r.get("qualification_status")
                if r.get("defining") is not None:
                    check(type(r.get("defining")) is bool, f"{prefix} {tag}: defining must be boolean")
                    check(not r.get("defining") or r.get("mandatory") is True,
                          f"{prefix} {tag}: a defining ask must be mandatory")
                if r.get("mandatory") and type(score) is int:
                    check(qs != "supported" or score >= 3,
                          f"{prefix} {tag}: supported needs a score of 3 or more")
                    check(qs != "unresolved" or score <= 2 or bool(r.get("threshold_note")),
                          f"{prefix} {tag}: a score of 3+ left unresolved needs threshold_note")
                    check(qs != "unmet" or bool(r.get("contradiction")),
                          f"{prefix} {tag}: unmet needs the contradicting dated record in contradiction")
            else:
                check(r.get("mandatory") in {None, False},
                      f"{prefix}: conditions cannot be mandatory scored asks")
        # A job stopped at the knockout screen with asks left unrated has no fit.
        skipped_l3 = status == "deprioritized" and j.get("fit_percent") is None
        if shared and (status in {"evaluation_error", "excluded"} or skipped_l3):
            check(j.get("baseline_fit") is None and not j.get("adjustment", 0),
                  f"{prefix}: unscored jobs cannot carry a baseline or adjustment")
        expected = None
        if status == "evaluation_error":
            check(j.get("fit_percent") is None, f"{prefix}: evaluation error must have null fit")
        elif not skipped_l3:
            try:
                if shared and status != "excluded":
                    calculated = evaluation.assess(requirements, j.get("adjustment", 0), j.get("adjustment_reason"), policy)
                    expected = calculated["functional_fit"]
                    check(j.get("baseline_fit") == calculated["baseline_fit"], f"{prefix}: baseline differs from shared calculation")
                else:
                    expected = fit(requirements)
                check(j.get("fit_percent") == expected, f"{prefix}: fit_percent {j.get('fit_percent')} != computed {expected}")
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
                errors.append(f"{prefix}: scoring failed: {e}")
        if shared:
            errors.extend(check_label(j, prefix, run))
        check(j.get("functional_fit") == expected,
              f"{prefix}: functional_fit does not equal the computed fit")
        # Jobs not scored at L3 (errors, and deprioritized jobs stopped at L2) carry no assessment fields.
        unassessed = status == "evaluation_error" or skipped_l3
        check(j.get("eligibility") in (ELIGIBILITY | {None} if unassessed else ELIGIBILITY),
              f"{prefix}: invalid eligibility")
        check(j.get("application_confidence") in (CONFIDENCE | {None} if unassessed else CONFIDENCE),
              f"{prefix}: invalid application_confidence")
        if not unassessed:
            check(bool(j.get("confidence_reason")), f"{prefix}: missing confidence_reason")
        mandatory_checks = [r.get("qualification_status") for r in requirements
                            if r.get("kind") != "condition" and r.get("mandatory") is True]
        condition_checks = [r.get("condition_status") for r in requirements
                            if r.get("kind") == "condition"]
        if not unassessed:
            if j.get("eligibility") == "pass":
                check(all(x == "supported" for x in mandatory_checks)
                      and all(x == "pass" for x in condition_checks),
                      f"{prefix}: eligibility pass despite unresolved mandatory ask or condition")
            if j.get("eligibility") == "fail":
                check(status == "excluded", f"{prefix}: eligibility fail needs excluded status")
            if j.get("eligibility") == "unresolved":
                check(status in {"needs_verification", "deprioritized"},
                      f"{prefix}: unresolved eligibility needs needs_verification status")
            if status == "eligible":
                check(j.get("eligibility") == "pass", f"{prefix}: eligible status requires eligibility pass")
        exclusion = j.get("exclusion")
        if status == "excluded":
            check(isinstance(exclusion, dict) and all(exclusion.get(k) for k in ("requirement_quote", "reason", "basis")),
                  f"{prefix}: excluded job requires documented exclusion")
            if isinstance(exclusion, dict):
                check(exclusion.get("basis") == "explicit_condition",
                      f"{prefix}: invalid exclusion basis")
        else:
            check(exclusion is None, f"{prefix}: nonexcluded job must not have exclusion")
        if status == "eligible":
            check(not any(r.get("kind") == "condition" and r.get("condition_status") != "pass" for r in requirements),
                  f"{prefix}: eligible job has unresolved/failed condition")
        errors.extend(check_dates_and_card(j, prefix, run.get("run_date")))
        if status not in {"evaluation_error", "excluded"}:
            if shared:
                errors.extend(check_coverage(j, artifacts_dir))
            screen = j.get("screen")
            if not isinstance(screen, dict):
                errors.append(f"{prefix}: job needs a screen object (L2 routing)")
                continue
            gaps = critical_gaps(requirements)
            check(sorted(screen.get("critical_gaps") or []) == sorted(gaps),
                  f"{prefix}: screen.critical_gaps {screen.get('critical_gaps')} != computed {gaps}")
            expected_route = routing(requirements)
            check(screen.get("routing") == expected_route,
                  f"{prefix}: screen.routing {screen.get('routing')} != computed {expected_route}")
            check((status == "deprioritized") == (expected_route == "deprioritized"),
                  f"{prefix}: status must be deprioritized exactly when L2 routing is deprioritized")
            if expected_route == "deprioritized":
                check(bool(screen.get("reason")), f"{prefix}: deprioritized job needs a one-line screen.reason")
    return errors

def check_dates_and_card(j, prefix, run_date):
    """Schema 1.3: posting dates, a passed deadline, and the card object on review-queue jobs."""
    errors = []
    if "posted_date" not in j or not (j["posted_date"] is None or DATE.fullmatch(str(j["posted_date"]))):
        errors.append(f"{prefix}: posted_date must be YYYY-MM-DD or null")
    deadline = j.get("deadline")
    if deadline is not None and not DATE.fullmatch(str(deadline)):
        errors.append(f"{prefix}: deadline must be YYYY-MM-DD or null")
    elif deadline and run_date and deadline < run_date and j.get("status") != "evaluation_error":
        errors.append(f"{prefix}: deadline {deadline} passed before run_date {run_date}; status must be evaluation_error")
    if j.get("status") == "evaluation_error" and not j.get("error_reason"):
        errors.append(f"{prefix}: evaluation_error needs error_reason")
    if j.get("status") in {"eligible", "needs_verification"}:
        card = j.get("card")
        if not isinstance(card, dict):
            return errors + [f"{prefix}: review-queue job needs a card object"]
        for k in ("business", "owns"):
            if not (isinstance(card.get(k), str) and card[k].strip()):
                errors.append(f"{prefix}: card.{k} is required")
        for k in CARD_TEXT:
            if k in card and not (isinstance(card[k], str) and card[k].strip()):
                errors.append(f"{prefix}: card.{k} must be text; leave out what the posting does not state")
        resp = card.get("responsibilities")
        if not (isinstance(resp, list) and 1 <= len(resp) <= 3 and all(isinstance(x, str) and x.strip() for x in resp)):
            errors.append(f"{prefix}: card.responsibilities needs 1-3 quotes")
        if not j.get("strongest_evidence"):
            errors.append(f"{prefix}: strongest_evidence is required on a review card")
    return errors


def summary(run):
    jobs = run["jobs"]
    statuses = STATUSES
    out = {"discovered": run["discovered_count"], "unique": len(jobs),
           "duplicates": run.get("duplicate_count", 0),
           **{status: sum(j["status"] == status for j in jobs) for status in sorted(statuses)},
           **{decision: sum(j["decision"] == decision for j in jobs) for decision in sorted(DECISIONS)}}
    if any("label" in j for j in jobs):
        out["labels"] = {l: sum(j.get("label") == l for j in jobs) for l in evaluation.LABELS}
    out["review_queue"] = len(review_queue(run))
    return out


def review_queue(run, include_all=False):
    """Jobs shown to the user, in review order. Gates first, fit last:
    eligibility pass before unresolved, then fewer critical gaps, then confidence, then fit.
    Deprioritized, excluded and errored jobs stay in the run file and are hidden unless include_all.
    Under shared-2 the label decides: Promising, then Stretch, are shown; Deprioritize is counted only."""
    def visible(j):
        if "label" in j:  # shared-2: the shared label decides what the user sees
            return j["label"] in {evaluation.PROMISING, evaluation.STRETCH}
        return j["status"] in {"eligible", "needs_verification"}
    jobs = [j for j in run["jobs"] if include_all or visible(j)]
    rank = {evaluation.PROMISING: 0, evaluation.STRETCH: 1, evaluation.DEPRIORITIZE: 2}
    def key(j):
        gaps = len((j.get("screen") or {}).get("critical_gaps") or critical_gaps(j.get("requirements", [])))
        fitv = j.get("functional_fit", j.get("fit_percent"))
        return (not visible(j), rank.get(j.get("label"), 3), j.get("eligibility") != "pass", gaps,
                CONFIDENCE_ORDER.get(j.get("application_confidence"), 3), -(fitv if fitv is not None else -1))
    return sorted(jobs, key=key)


# --- L1 hard gates and the capability profile (need PyYAML) ---------------------------------------

def load_yaml(path):
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def has_place(text, place):
    """Whole-word match, so 'india' does not match 'Indianapolis'. Places such as ', nj' keep their comma."""
    return re.search(r"(?<![a-z])" + re.escape(place.strip()) + r"(?![a-z])", text) is not None


def url_place(url):
    """HiringCafe job URLs end with '<city>-<state>-<job id>'; the location text sometimes drops the state."""
    slug = re.sub(r"[?#].*", "", url or "").rstrip("/").rsplit("/", 1)[-1]
    return slug.replace("-", " ")


PAY_UNITS = {"yr": 1, "year": 1, "annually": 1, "mo": 12, "month": 12, "wk": 52, "week": 52, "hr": 2080, "hour": 2080}


def pay_top(text):
    """Top of a posted US-dollar range as annual pay, or None when pay is absent or unreadable.
    '$93,500 – $177,590/yr' -> 177590; '$60/hr' -> 124800 (2,080 hours)."""
    if not text or "$" not in text:
        return None
    amounts = [float(a.replace(",", "")) * (1000 if k.lower() == "k" else 1)
               for a, k in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)\s?([kK]?)", text)]
    unit = re.search(r"/\s?(yr|year|mo|month|wk|week|hr|hour)\b|\b(annually)\b", text, re.I)
    factor = PAY_UNITS[(unit.group(1) or unit.group(2)).lower()] if unit else 1
    return max(amounts) * factor if amounts else None


def screen_job(job, conditions, artifacts_dir=None, cache=None, run_date=None, max_age_days=None, min_pay=None):
    """L1 for one job: posting dates, completeness and stated conditions. Returns (result, reasons).
    result: evaluation_error | fail | unknown | pass. Never scores asks."""
    reasons = []
    deadline, posted = job.get("deadline"), job.get("posted_date")
    if run_date and deadline and str(deadline) < run_date:
        return "evaluation_error", [f"application deadline {deadline} has passed"]
    if run_date and max_age_days and posted and DATE.fullmatch(str(posted)):
        age = (datetime.date.fromisoformat(run_date) - datetime.date.fromisoformat(posted)).days
        if age > max_age_days:
            return "evaluation_error", [f"posted {age} days ago, beyond the {max_age_days}-day search window"]
    art = job.get("jd_artifact")
    if artifacts_dir and isinstance(art, dict) and art.get("artifact_id"):
        artifact, _, errs = load_jd_artifact(artifacts_dir, art["artifact_id"], cache if cache is not None else {})
        if errs:
            return "evaluation_error", [f"JD artifact invalid: {errs[0]}"]
        status = artifact["source"]["completeness"]["status"]
        if status == "truncated":
            return "evaluation_error", ["JD truncated by the provider; fetch the full posting before scoring"]
        if status == "insufficient":
            return "evaluation_error", ["JD too short to be a posting (provider stub); fetch the employer's posting before scoring"]
        if status == "unknown":
            reasons.append("JD completeness not asserted")
    if "radius_miles" in conditions:  # current shared rules (tools/conditions.py), also used by Stage 1
        url = job.get("posting_url") if job.get("provider") == "hiringcafe" else None
        result, found = shared_conditions.check(job.get("location"), job.get("workplace"), conditions,
                                                job.get("travel_percent"), url)
        reasons += found
        top = pay_top(job.get("compensation"))
        if result in {"pass", "unknown"} and min_pay and top is not None and top < min_pay:
            result = "fail"
            reasons.append(f"posted pay tops out at ${top:,.0f}, below the ${min_pay:,.0f} minimum")
        return result, reasons
    # Legacy place-list rules, kept unchanged so runs frozen with them revalidate identically.
    loc = (job.get("location") or "").lower()
    workplace = (job.get("workplace") or "").lower()
    places = [p.lower() for p in conditions.get("metro_places", [])]
    result = "pass"
    if not loc:
        result = "unknown"
        reasons.append("no location stated; confirm the permitted work region")
    elif "remote" in workplace and (any(has_place(loc, p) for p in ("united states", "usa", "us")) or
                                    not any(has_place(loc, x) for x in conditions.get("remote_excluded_regions", []))):
        reasons.append("remote role")
    elif any(has_place(loc, p) for p in places):
        reasons.append("location inside the preferred metro")
    elif job.get("provider") == "hiringcafe" and any(has_place(url_place(job.get("posting_url")), p) for p in places):
        reasons.append("location inside the preferred metro (state taken from the posting URL)")
    else:
        result = "fail"
        reasons.append(f"location '{job.get('location')}' with workplace '{job.get('workplace')}' is outside the preferred metro")
    top = pay_top(job.get("compensation"))
    if result in {"pass", "unknown"} and min_pay and top is not None and top < min_pay:
        result = "fail"
        reasons.append(f"posted pay tops out at ${top:,.0f}, below the ${min_pay:,.0f} minimum")
    travel = job.get("travel_percent")
    if result == "pass" and isinstance(travel, (int, float)) and travel > conditions.get("travel_percent_max", 50):
        result = "unknown"
        reasons.append(f"travel {travel}% is above the confirmed {conditions.get('travel_percent_max', 50)}%; ask")
    return result, reasons


def career_ids(repo=None):
    """Every record ID in the career collections (shared with Stage 1: tools/evaluation.py)."""
    return evaluation.career_ids(repo)


def check_profile(profile, repo=None):
    """Errors for a capability profile; staleness is returned separately as warnings."""
    errors, warnings = [], []
    repo = Path(repo) if repo else CAREER_REPO
    if not re.fullmatch(r"[a-f0-9]{40}", str(profile.get("career_commit", ""))):
        errors.append("career_commit must be a 40-character SHA")
    known = career_ids(repo)
    seen = set()
    if "competencies" in profile:
        errors.append("use strengths and partials; the profile lists no 'no' entries")
    for section, allowed in (("strengths", {3, 4}), ("partials", {2})):
        for c in profile.get(section) or []:
            cid = c.get("id")
            if not cid or cid in seen:
                errors.append(f"missing or duplicate capability id {cid}")
            seen.add(cid)
            if c.get("score") not in allowed:
                errors.append(f"{cid}: {section} entries score {sorted(allowed)}; record gaps as limits on a strength")
            if not c.get("record_ids"):
                errors.append(f"{cid}: needs at least one record_id")
            for rid in c.get("record_ids", []):
                if rid not in known:
                    errors.append(f"{cid}: unknown record {rid}")
    import subprocess
    try:
        # Evidence records only: preferences and search criteria are not evidence.
        changed = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", profile.get("career_commit", ""),
                                  "HEAD", "--", "career", ":(exclude)career/preferences.md",
                                  ":(exclude)career/search-criteria.yaml",
                                  ":(exclude)career/capability-profile.yaml"], capture_output=True, text=True, timeout=30)
        if changed.returncode == 0 and changed.stdout.strip():
            warnings.append("career records changed since career_commit; review the profile: "
                            + ", ".join(changed.stdout.split()[:8]))
        elif changed.returncode != 0:
            warnings.append("could not compare career_commit with HEAD (commit missing locally?)")
    except (OSError, subprocess.SubprocessError):
        warnings.append("git unavailable; staleness not checked")
    return errors, warnings

# --- Review cards (schema 1.3) --------------------------------------------------------------------

CARD_PAGE = Path(__file__).with_name("cards.html")


def days_between(a, b):
    try:
        return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return None


def card_data(run):
    """The review queue as plain data for the cards page: the job first, the fit details after."""
    cards = []
    for j in review_queue(run):
        card = j.get("card") or {}
        reqs = j.get("requirements", [])
        gap_ids = set((j.get("screen") or {}).get("critical_gaps") or critical_gaps(reqs))
        open_asks = [r for r in reqs if r.get("mandatory") and r.get("qualification_status") == "unresolved"
                     and r.get("competency_id") not in gap_ids]
        open_conditions = [r for r in reqs if r.get("kind") == "condition" and r.get("condition_status") != "pass"]
        cards.append({
            "id": j["id"], "company": j["company"], "title": j["title"], "url": j["posting_url"],
            "location": j.get("location"), "workplace": j.get("workplace"), "pay": j.get("compensation"),
            "posted": j.get("posted_date"), "age": days_between(j.get("posted_date"), run.get("run_date")),
            "deadline": j.get("deadline"), "fit": j.get("functional_fit", j.get("fit_percent")),
            "evaluation_policy": j.get("evaluation_policy"), "baseline_fit": j.get("baseline_fit"),
            "adjustment": j.get("adjustment", 0), "adjustment_reason": j.get("adjustment_reason"),
            **{k: card.get(k) for k in CARD_TEXT}, "responsibilities": card.get("responsibilities") or [],
            "must_haves": must_haves(j), "status": j["status"], "label": j.get("label"),
            "requirements_met": j.get("requirements_met"), "stale": j.get("stale_posting", False),
            "gaps": [r["quote"] for r in reqs if r.get("competency_id") in gap_ids],
            "verify": [r["quote"] for r in open_asks + open_conditions] +
                      ((j.get("l1") or {}).get("reasons", []) if (j.get("l1") or {}).get("l1") == "unknown" else []),
            "inferred_concerns": j.get("inferred_concerns") or [],
            "confidence": j.get("application_confidence"), "confidence_reason": j.get("confidence_reason"),
            "strongest": j.get("strongest_evidence"), "gap": j.get("primary_gap")})
    s = summary(run)
    hidden = {k: s.get(k, 0) for k in ("deprioritized", "evaluation_error", "excluded")}
    if "labels" in s:  # shared-2: every Deprioritize label, whatever stopped it
        hidden["deprioritized"] = sum(1 for j in run["jobs"] if j.get("label") == evaluation.DEPRIORITIZE
                                      and j["status"] != "excluded")
    done = run.get("completion") or {}
    return {"run_id": run.get("run_id"), "run_date": run.get("run_date"), "commit": str(run.get("source_commit"))[:7],
            "source_commit": run.get("source_commit"), "selection_key": selection_key(run),
            "cards": cards, "hidden": hidden, "completion": {"status": done.get("status", "not checked"),
                                                            "progress": (done.get("cards") or {}).get("line"),
                                                            "problems": (done.get("problems") or [])[:8]}}


def render_cards(run):
    """Self-contained HTML for the review page. Publish it as an artifact with the capabilities in
    job-search/README.md so Pass and Interested save; opened anywhere else it keeps choices in the browser.
    Its Download my choices button writes the file pipeline.py decide reads."""
    data = json.dumps(card_data(run), ensure_ascii=False).replace("</", "<\\/")
    return CARD_PAGE.read_text(encoding="utf-8").replace("/*DATA*/null", data)


def apply_decisions(run, decisions):
    """Copy Pass/Interested choices into the run. Accepts the cards page's "Download my choices" file
    ({"kind": "decisions", "run_id", "decisions": {job id: decision}}) or a bare {job id: decision} map."""
    if isinstance(decisions.get("decisions"), dict):
        if decisions.get("run_id") != run.get("run_id"):
            raise ValueError(f"choices are for run {decisions.get('run_id')}, not {run.get('run_id')}")
        if decisions.get("source_commit") not in (None, run.get("source_commit")):
            raise ValueError("choices are from a different source revision")
        if decisions.get("selection_key") not in (None, selection_key(run)):
            raise ValueError("choices are from a different set of cards")
        decisions = decisions["decisions"]
    by_id = {j["id"]: j for j in run["jobs"]}
    unknown = [k for k in decisions if k not in by_id]
    bad = [k for k, v in decisions.items() if v not in DECISIONS]
    if unknown or bad:
        raise ValueError(f"unknown job ids {unknown[:5]} or invalid decisions {bad[:5]}")
    for k, v in decisions.items():
        by_id[k]["decision"] = v
    return {d: sum(j["decision"] == d for j in run["jobs"]) for d in sorted(DECISIONS)}


def selection_key(run):
    return object_hash({"run_id": run.get("run_id"), "run_date": run.get("run_date"),
                        "source_commit": run.get("source_commit"), "jobs": sorted(j["id"] for j in run["jobs"])})


# --- Handoff: the application queue export --------------------------------------------------------

APPLICATION_STATUSES = ("not_started", "resume_ready", "applied", "closed")


def export_queue(run, artifacts_dir=None, exported_on=None):
    """The handoff from search and select to applications: every Interested job as a self-contained record.
    Each record carries the posting text, so a receiving agent or tool needs nothing else from this run.
    Interest (decision) and application progress (application_status) are separate fields."""
    cache, items = {}, []
    for j in review_queue(run, include_all=True):
        if j.get("decision") != "interested":
            continue
        reqs = j.get("requirements", [])
        gap_ids = set((j.get("screen") or {}).get("critical_gaps") or critical_gaps(reqs))
        posting = None
        art = j.get("jd_artifact") or {}
        if artifacts_dir and art.get("artifact_id"):
            artifact, canonical, errs = load_jd_artifact(artifacts_dir, art["artifact_id"], cache)
            if not errs:
                posting = {"text": canonical, "sha256": artifact["canonical"]["sha256"],
                           "completeness": artifact["source"]["completeness"]["status"],
                           "source_type": artifact["source"]["type"]}
        items.append({
            "job_id": j["id"], "company": j["company"], "title": j["title"], "posting_url": j["posting_url"],
            **{k: j.get(k) for k in ("provider", "provider_job_id", "location", "workplace", "compensation",
                                     "posted_date", "deadline")},
            "decision": "interested", "application_status": "not_started",
            "screening": {"status": j["status"], "label": j.get("label"), "requirements_met": j.get("requirements_met"),
                          "fit_percent": j.get("functional_fit", j.get("fit_percent")),
                          "eligibility": j.get("eligibility"), "application_confidence": j.get("application_confidence"),
                          "confidence_reason": j.get("confidence_reason"),
                          "critical_gaps": [r["quote"] for r in reqs if r.get("competency_id") in gap_ids],
                          "to_verify": [r["quote"] for r in reqs if r.get("mandatory")
                                        and r.get("qualification_status") == "unresolved"
                                        and r.get("competency_id") not in gap_ids],
                          "strongest_evidence": j.get("strongest_evidence"), "primary_gap": j.get("primary_gap")},
            "card": j.get("card"), "must_haves": must_haves(j), "posting": posting})
    return {"export_version": "1.0", "kind": "application_queue",
            "exported_on": exported_on or datetime.date.today().isoformat(),
            "source": {"run_id": run.get("run_id"), "run_date": run.get("run_date"),
                       "source_commit": run.get("source_commit"),
                       "completion": (run.get("completion") or {}).get("status", "not checked")},
            "counts": {d: sum(j.get("decision") == d for j in run["jobs"]) for d in sorted(DECISIONS)},
            # False means the user's choices were never imported (pipeline.py decide); the queue is not their selection.
            "choices_imported": any(j.get("decision") != "undecided" for j in run["jobs"]),
            "jobs": items}


# --- Run control: plan, freeze, per-job results, status (decided by code, not by the agent) ----------

def sha256_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_name(job_id):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", job_id)


def plan(criteria, provider="hiringcafe", target=None):
    """The exact searches a run must perform: every title of every family, the remote pass (first title of
    each family) and every domain. Each search has a stable id the agent logs in search_log.json."""
    search, adapter = criteria["search"], (criteria.get("providers") or {}).get(provider, {})
    if not search.get("role_families"):
        raise ValueError("career/search-criteria.yaml has no role families yet; fill the search criteria first "
                         "(agents/job-search.md, Prepare)")
    cond = criteria.get("conditions") or {}
    home, radius = cond.get("center"), cond.get("radius_miles")
    if not home:
        raise ValueError("career/search-criteria.yaml has no conditions.center yet; record where you search from")
    industries = adapter.get("domain_industries") or {}
    out = []
    for fam in search["role_families"]:
        for i, title in enumerate(fam["titles"], 1):
            out.append({"id": f"{fam['id']}:{i}", "family": fam["id"], "tier": fam["tier"], "kind": "title", "text": title})
        out.append({"id": f"{fam['id']}:remote", "family": fam["id"], "tier": fam["tier"], "kind": "remote",
                    "text": fam["titles"][0], "workplace": "Remote", "location": "United States"})
    for d in search.get("domains", []):
        entry = {"id": f"domain:{d['id']}", "family": d["id"], "tier": "domain", "kind": "domain"}
        if d["id"] in industries:
            entry.update(text="product manager", industries=industries[d["id"]])
        else:
            entry.update(text=f"product manager {d['keywords']}")
        out.append(entry)
    for query in out:
        query["requested_filters"] = {"search": query["text"],
            "location": query.get("location", home),
            "posted_within_days": search.get("max_posting_age_days"),
            "seniority_levels": adapter.get("seniority_levels", [])}
        if query.get("workplace"):
            query["requested_filters"]["workplace_types"] = [query["workplace"]]
        else:
            query["requested_filters"]["radius_miles"] = radius or 50
        if query.get("industries"):
            query["requested_filters"]["industries"] = query["industries"]
    cards = target or search["target_cards"]
    return {"workflow_version": 2, "criteria": criteria, "provider": provider, **card_budget(search, cards),
            "max_posting_age_days": search.get("max_posting_age_days"), "results_per_query": search.get("results_per_query"),
            "adapter": adapter, "searches": out}


TIER_ORDER = {"core": 0, "strong": 1, "exploratory": 2, "broad": 3, "domain": 4}
CARD_LABELS = {evaluation.PROMISING, evaluation.STRETCH}


def card_budget(search, cards):
    """The user names the number of review cards (Promising and Stretch). The run fetches a first batch of
    first_batch_multiplier x cards, tops up in batches until the cards are reached, and never fetches more
    than max_fetch_multiplier x cards in total."""
    cards = int(cards)
    if cards < 1:
        raise ValueError("target cards must be at least 1")
    return {"target_cards": cards,
            "first_batch": math.ceil(cards * search.get("first_batch_multiplier", 1.5)),
            "fetch_cap": math.ceil(cards * search.get("max_fetch_multiplier", 3)),
            "top_up_min": search.get("top_up_batch_min", 5)}


def title_words(text, stopwords):
    return {w for w in re.findall(r"[a-z0-9&]+", (text or "").lower()) if w not in stopwords}


def candidates(plan_doc, log, criteria, run_date, target=None):
    """Which jobs to fetch, decided by code from the logged search results.
    Drops results posted more than max_posting_age_days before run_date (no date: kept), results whose title
    shares no word with the search's family titles once title_stopwords are ignored, and repeats of a job
    (same id, or same company and title). Then takes jobs round-robin across families, core tier first in
    each round, until the target. Every result gets a recorded reason."""
    search = criteria["search"]
    stop = {w.lower() for w in search.get("title_stopwords", [])}
    max_age = search.get("max_posting_age_days")
    target = target or plan_doc.get("first_batch") or plan_doc["target_unique_jobs"]
    if plan_doc.get("fetch_cap"):
        target = min(target, plan_doc["fetch_cap"])
    fam_titles = {f["id"]: [t for t in f["titles"]] for f in search["role_families"]}
    meta = {x["id"]: x for x in plan_doc["searches"]}
    queues, order, decisions, eligible, keys = {}, [], [], {}, {}
    logged = {e["id"]: e for e in log.get("searches", [])}
    for m in plan_doc["searches"]:
        entry = logged.get(m["id"], {})
        if entry.get("status") != "run":
            continue
        fam = m["family"]
        if fam not in queues:
            queues[fam] = []
            order.append((TIER_ORDER.get(m["tier"], 9), len(order), fam))
        words = set().union(*(title_words(t, stop) for t in fam_titles.get(fam, [m["text"]])))
        for item in entry.get("items", []):
            rec = {"job_id": item["job_id"], "company": item.get("company"), "title": item.get("title"),
                   "posted_date": item.get("posted_date"), "search": entry["id"], "family": fam}
            age = days_between(item.get("posted_date"), run_date)
            if max_age and age is not None and age > max_age:
                rec["reason"] = f"posted {age} days ago"
            elif not (title_words(item.get("title"), stop) & words):
                rec["reason"] = "title shares no word with the family"
            else:
                # Rejecting an occurrence never poisons later occurrences. Missing
                # location is not enough evidence to merge two different job IDs.
                loc = " ".join(sorted(re.split(r"\s+or\s+", (item.get("location") or "").casefold())))
                key = (str(item.get("company", "")).casefold().strip(),
                       str(item.get("title", "")).casefold().strip(), loc)
                canonical = item["job_id"] if item["job_id"] in eligible else keys.get(key) if loc else None
                if canonical is None:
                    canonical = item["job_id"]
                    eligible[canonical] = rec
                    if loc:
                        keys[key] = canonical
                    rec["reason"] = None
                else:
                    rec["reason"] = "repeat"
                rec["canonical_id"] = canonical
                if canonical not in queues[fam]:
                    queues[fam].append(canonical)
            decisions.append(rec)
    selected, rank = [], 0
    families = [f for _, _, f in sorted(order)]
    while len(selected) < target and any(queues[f] for f in families):
        rank += 1
        for fam in families:
            while queues[fam] and queues[fam][0] in selected:
                queues[fam].pop(0)
            if queues[fam] and len(selected) < target:
                jid = queues[fam].pop(0)
                selected.append(jid)
                eligible[jid].update(reason="selected", round=rank)
    for rec in eligible.values():
        if rec["reason"] is None:
            rec["reason"] = "not reached (target met)"
    return {"run_date": run_date, "target": target, "selected": selected,
            "plan_sha256": object_hash(plan_doc), "search_log_sha256": object_hash(log),
            "selection_criteria": criteria,
            "counts": {"results": len(decisions), "selected": len(selected),
                       **{k: sum(r["reason"] == k for r in decisions) for k in ("repeat", "not reached (target met)")},
                       "too old": sum(str(r["reason"]).startswith("posted") for r in decisions),
                       "title mismatch": sum(r["reason"] == "title shares no word with the family" for r in decisions)},
            "results": decisions}


def freeze(jobs_doc, run_id, run_date, source_commit, frozen_input=False, l1_rules=None):
    """The manifest: which jobs this run must finish, with their posting hashes. Written once after intake."""
    jobs = jobs_doc["jobs"]
    return {"run_id": run_id, "run_date": run_date, "source_commit": source_commit, "frozen_input": frozen_input,
            **({"workflow_version": 2, "l1_rules": l1_rules} if l1_rules is not None else {}),
            "discovered": jobs_doc.get("discovered", len(jobs)), "duplicates": jobs_doc.get("duplicates", 0),
            "jobs": [{"id": j["id"], "result_file": f"results/{safe_name(j['id'])}.json", "aliases": j.get("aliases", []),
                      "artifact_id": (j.get("jd_artifact") or {}).get("artifact_id"),
                      "canonical_sha256": (j.get("jd_artifact") or {}).get("canonical_sha256"),
                      "input_sha256": object_hash(j)} for j in jobs]}


def add_batch(manifest, jobs_doc):
    """Append newly fetched jobs (a top-up batch) to a frozen manifest. Earlier entries must still match
    their posting inputs; they are never rewritten. Returns the ids added."""
    jobs = {j["id"]: j for j in jobs_doc["jobs"]}
    for e in manifest["jobs"]:
        if e["id"] not in jobs or object_hash(jobs[e["id"]]) != e["input_sha256"]:
            raise ValueError(f"{e['id']}: frozen posting inputs changed or missing; a batch only adds jobs")
    known = {e["id"] for e in manifest["jobs"]}
    added = [j for j in jobs_doc["jobs"] if j["id"] not in known]
    manifest["jobs"] += [{"id": j["id"], "result_file": f"results/{safe_name(j['id'])}.json", "aliases": j.get("aliases", []),
                          "artifact_id": (j.get("jd_artifact") or {}).get("artifact_id"),
                          "canonical_sha256": (j.get("jd_artifact") or {}).get("canonical_sha256"),
                          "input_sha256": object_hash(j)} for j in added]
    manifest["discovered"] = jobs_doc.get("discovered", len(jobs_doc["jobs"]))
    manifest["duplicates"] = jobs_doc.get("duplicates", 0)
    manifest.setdefault("batches", [[e["id"] for e in manifest["jobs"] if e["id"] not in {j["id"] for j in added}]])
    manifest["batches"].append([j["id"] for j in added])
    return [j["id"] for j in added]


def card_progress(run_dir):
    """Cards ready (Promising or Stretch), jobs evaluated, jobs fetched, and whether the run can still top up."""
    run_dir = Path(run_dir)
    m = load_json(run_dir / "manifest.json")
    pl = load_json(run_dir / "plan.json") if (run_dir / "plan.json").exists() else {}
    results = [load_json(run_dir / e["result_file"]) for e in m["jobs"] if (run_dir / e["result_file"]).exists()]
    cand = load_json(run_dir / "candidates.json") if (run_dir / "candidates.json").exists() else {}
    remaining = sum(r.get("reason") == "not reached (target met)" for r in cand.get("results", []))
    selected = len(cand.get("selected", []))
    out = {"target_cards": pl.get("target_cards"), "cards": sum(r.get("label") in CARD_LABELS for r in results),
           "evaluated": len(results), "fetched": len(m["jobs"]), "selected": selected,
           "fetch_cap": pl.get("fetch_cap"), "pool_exhausted": bool(cand) and remaining == 0,
           "cap_reached": bool(pl.get("fetch_cap")) and selected >= pl["fetch_cap"]}
    out["target_met"] = out["target_cards"] is not None and out["cards"] >= out["target_cards"]
    out["line"] = (f"{out['cards']} of {out['target_cards']} cards ready · {out['evaluated']} of {out['fetched']} "
                   f"fetched postings evaluated")
    return out


def top_up(run_dir):
    """Extend the candidate selection after every fetched job has a result and the cards fall short.
    The deterministic order is unchanged, so earlier picks stay; only new ids are added."""
    run_dir = Path(run_dir)
    prog = card_progress(run_dir)
    pl = load_json(run_dir / "plan.json")
    if prog["evaluated"] < prog["fetched"]:
        return {"action": "evaluate", "reason": "evaluate every fetched posting before topping up", **prog}
    if prog["target_met"]:
        return {"action": "none", "reason": "card target reached", **prog}
    if prog["pool_exhausted"] or prog["cap_reached"]:
        why = "search results exhausted" if prog["pool_exhausted"] else f"fetch cap of {pl['fetch_cap']} reached"
        return {"action": "none", "reason": f"{why}; {prog['cards']} of {prog['target_cards']} cards", **prog}
    cand = load_json(run_dir / "candidates.json")
    needed = prog["target_cards"] - prog["cards"]
    mult = pl["criteria"]["search"].get("first_batch_multiplier", 1.5)
    new_target = min(pl["fetch_cap"], len(cand["selected"]) + max(pl.get("top_up_min", 5), math.ceil(needed * mult)))
    log = load_json(run_dir / "search_log.json")
    fresh = candidates(pl, log, cand.get("selection_criteria", pl["criteria"]), cand["run_date"], new_target)
    if fresh["selected"][:len(cand["selected"])] != cand["selected"]:
        raise ValueError("deterministic selection changed; earlier picks must stay a prefix")
    fresh["batches"] = cand.get("batches", [cand["selected"]]) + [fresh["selected"][len(cand["selected"]):]]
    (run_dir / "candidates.json").write_text(json.dumps(fresh, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"action": "fetch", "fetch": fresh["batches"][-1], "new_target": new_target, **card_progress(run_dir)}


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def check_coverage(job, artifacts_dir):
    """Require a complete guarded JD map and account for every selected ask once.
    Semantic choice of what to skip/merge remains agent judgment, not certification.
    """
    import jd_ingest
    prefix = job.get("id", "job")
    art_id = (job.get("jd_artifact") or {}).get("artifact_id")
    if not artifacts_dir or not art_id:
        return [f"{prefix}: shared evaluation needs the full JD artifact and --artifacts"]
    directory = Path(artifacts_dir) / art_id
    artifact, _, errors = jd_ingest.validate_dir(directory)
    if errors:
        return [f"{prefix}: invalid JD artifact for coverage"]
    selections = artifact.get("selections") or {}
    if not selections.get("map"):
        return [f"{prefix}: render a complete JD selection/skip map before evaluation"]
    code, _, errors, _ = jd_ingest.render(directory, "\n".join(selections["map"]), record=False)
    if code:
        return [f"{prefix}: JD coverage map is incomplete or invalid: {errors}"]
    coverage = job.get("coverage") or {}
    if coverage.get("map_sha256") != selections["map_sha256"]:
        return [f"{prefix}: coverage map hash missing or stale"]
    selected = {s["tag"] for s in selections["items"]}
    accounted, problems = set(), []
    for req in job.get("requirements", []):
        tags = req.get("source_tags")
        if not isinstance(tags, list) or not tags:
            problems.append(f"{prefix}: every measured ask needs source_tags")
            continue
        for tag in tags:
            if tag not in selected or tag in accounted:
                problems.append(f"{prefix}: unknown or multiply mapped source tag {tag}")
            accounted.add(tag)
        if req.get("kind") != "condition":
            try:
                problem = evaluation.check_kind(req.get("kind"), tags)
            except ValueError:
                problem = f"unknown source tag kind in {tags}"
            if problem:
                problems.append(f"{prefix}: {problem}")
        if any(str(tag).startswith("Cond-") for tag in tags) and (
                req.get("kind") != "condition" or not all(str(tag).startswith("Cond-") for tag in tags)):
            problems.append(f"{prefix}: conditions must stay separate from scored competencies")
        if req.get("quote_status") != "source_verified" or (req.get("source") or {}).get("tag") not in tags:
            problems.append(f"{prefix}: measured quotes need a verified reference to one of their source tags")
    deferred = coverage.get("deferred", {})
    if not isinstance(deferred, dict):
        problems.append(f"{prefix}: deferred asks must map tags to reasons")
        deferred = {}
    for tag, reason in deferred.items():
        if job.get("status") != "deprioritized" or job.get("functional_fit") is not None:
            problems.append(f"{prefix}: only an early-screened job can defer scoring selected asks")
        if tag not in selected or tag in accounted or not isinstance(reason, str) or not reason.strip():
            problems.append(f"{prefix}: invalid deferred source tag/reason {tag}")
        accounted.add(tag)
    if accounted != selected:
        problems.append(f"{prefix}: selected JD asks missing from evaluation: {sorted(selected - accounted)}")
    return problems


def l1_check(base, rules, run_date, artifacts_dir):
    if not (base.get("jd_artifact") or {}).get("artifact_id"):
        return {"l1": "evaluation_error", "reasons": ["full JD artifact missing"]}
    state, reasons = screen_job(base, rules["conditions"], artifacts_dir, {}, run_date,
                               rules.get("max_age_days"), rules.get("min_pay"))
    pay = base.get("provider_compensation") or {}
    if state == "pass" and pay and not base.get("compensation"):
        state = "unknown"
        reasons.append("compensation currency or frequency requires verification")
    if state == "pass" and (not base.get("posted_date") or "JD completeness not asserted" in reasons):
        state = "unknown"
        reasons.append("posting age or description completeness requires verification")
    return {"l1": state, "reasons": reasons}


def condition_failure(reqs):
    """The first condition the agent marked failed from the posting text, or None."""
    return next((r for r in reqs or [] if r.get("kind") == "condition" and r.get("condition_status") == "fail"), None)


def enforce_l1(job, base, manifest, artifacts_dir):
    """Compute L1 independently of the agent's scoring draft; never trust a label."""
    rules = manifest.get("l1_rules")
    if rules is None:
        return []  # historical runs stay readable; the current CLI always pins rules
    receipt = l1_check(base, rules, manifest["run_date"], artifacts_dir)
    errors = []
    expected = {"fail": "excluded", "evaluation_error": "evaluation_error"}.get(receipt["l1"])
    if expected and job.get("status") != expected:
        errors.append(f"{job['id']}: L1 requires {expected}: {'; '.join(receipt['reasons'])}")
    if not expected and job.get("status") == "excluded":
        failed = condition_failure(job.get("requirements"))
        if not (failed and (job.get("exclusion") or {}).get("requirement_quote") == failed.get("quote")):
            errors.append(f"{job['id']}: neither L1 nor a failed posting condition supports this exclusion")
    if receipt["l1"] == "unknown" and job.get("status") == "eligible":
        errors.append(f"{job['id']}: unresolved L1 conditions cannot be eligible")
    if job.get("l1") != receipt:
        errors.append(f"{job['id']}: L1 receipt missing or differs from recomputed check")
    return errors


def check_job(job, run_date, known_ids=None, artifacts_dir=None):
    """Validate one job result on its own (schema 1.3), as it would be inside the run."""
    mini = {"schema_version": "1.3", "run_id": "check", "run_date": run_date, "source_commit": "0" * 40,
            "search_criteria": "x", "discovered_count": 1, "duplicate_count": 0, "jobs": [job]}
    return [e.replace("jobs[0]", job.get("id", "job")) for e in validate(mini, artifacts_dir, known_ids=known_ids)]


BASE_FIELDS = ("id", "provider", "provider_job_id", "company", "title", "posting_url", "location", "workplace",
               "compensation", "provider_compensation", "posted_date", "deadline", "travel_percent", "jd_artifact", "found_by", "aliases")


def stale_posting(posted_date, run_date, stale_after_days):
    """True when the posting is older than the criteria's stale_after_days on the run date."""
    age = days_between(posted_date, run_date) if posted_date and run_date else None
    return bool(stale_after_days and age is not None and age > stale_after_days)


def job_label(job, stale=False):
    """The shared Promising / Stretch / Deprioritize decision for one search result (tools/evaluation.py)."""
    reqs = job.get("requirements", [])
    if job.get("status") == "evaluation_error":
        return {"label": None, "requirements_met": None, "critical_gaps": None, "stale_posting": bool(stale)}
    out = evaluation.decide(reqs, job.get("functional_fit"),
                            [r.get("condition_status") for r in reqs if r.get("kind") == "condition"],
                            knocked_out=(job.get("screen") or {}).get("routing") == "deprioritized", stale=stale)
    if job.get("status") == "excluded":
        out["label"] = evaluation.DEPRIORITIZE
    return out


def check_label(j, prefix, run):
    errors = []
    rules = run.get("l1_rules") or {}
    stale = j.get("stale_posting", False)
    if rules.get("stale_after_days") is not None:
        expected_stale = stale_posting(j.get("posted_date"), run.get("run_date"), rules["stale_after_days"])
        if stale != expected_stale:
            errors.append(f"{prefix}: stale_posting {stale} differs from the posting age")
    expected = job_label(j, stale)
    for k in ("label", "requirements_met"):
        if j.get(k) != expected[k]:
            errors.append(f"{prefix}: {k} {j.get(k)} differs from the shared rule ({expected[k]})")
    for r in j.get("requirements", []):
        if r.get("kind") != "condition" and r.get("source_tags") and bool(r.get("mandatory")) != evaluation.is_mandatory(r):
            errors.append(f"{prefix} {r.get('tag')}: mandatory must match its source tags (Want tags are the required asks)")
    return errors


def build_result(draft, base, policy=None, run_date=None, stale_after_days=None):
    """build_one plus, under shared-2, the shared label, requirements met and stale-posting flag."""
    job = build_one(draft, base, policy)
    if policy in evaluation.POLICIES:
        stale = stale_posting(job.get("posted_date"), run_date, stale_after_days)
        decided = job_label(job, stale)
        job.update(label=decided["label"], requirements_met=decided["requirements_met"], stale_posting=stale)
    return job


def build_one(draft, base, policy=None):
    """One job's result from the agent's judgments (draft) and the intake record (base, from jobs.json).
    The agent supplies requirements, card and confidence; code fills the posting facts and computes fit,
    critical gaps, routing, eligibility and status. Draft keys: requirements, card, application_confidence,
    confidence_reason, strongest_evidence, primary_gap, screen_reason; or status evaluation_error with
    error_reason, or status excluded with exclusion; l3: false for a job stopped at L2."""
    job = {k: base[k] for k in BASE_FIELDS if k in base}
    job.setdefault("posted_date", None)
    job.update({k: v for k, v in draft.items() if k not in {"l3", "screen_reason", "status"} and k not in BASE_FIELDS})
    job.update(decision="undecided", requirements=draft.get("requirements", []), exclusion=draft.get("exclusion"))
    reqs = job["requirements"]
    if policy in evaluation.POLICIES:
        job.update(evaluation_policy=policy, baseline_fit=None, adjustment=0, adjustment_reason=None)
    failed = condition_failure(reqs) if draft.get("status") not in {"evaluation_error", "excluded"} else None
    if failed:
        # A stated condition the agent reads in the posting text excludes the job, as Stage 1 deprioritizes it.
        if policy in evaluation.POLICIES and failed.get("quote_status") != "source_verified":
            raise ValueError("a failed condition needs a source-verified quote before it can exclude a job")
        job["exclusion"] = {"basis": "explicit_condition", "requirement_quote": failed["quote"], "source": "description",
                            "reason": failed.get("evidence_note") or f"posting condition conflicts with preferences: {failed['quote']}"}
        draft = dict(draft, status="excluded")
    if draft.get("status") in {"evaluation_error", "excluded"}:
        job.update(status=draft["status"], fit_percent=None, functional_fit=None, card=None,
                   eligibility="fail" if draft["status"] == "excluded" else None,
                   application_confidence=draft.get("application_confidence", "low" if draft["status"] == "excluded" else None))
        return job
    route = routing(reqs)
    job["screen"] = {"critical_gaps": critical_gaps(reqs), "routing": route, "reason": draft.get("screen_reason")}
    # A knocked-out job still gets a fit when every selected ask was rated; asks deferred at the screen
    # (coverage.deferred), or l3: false on a draft without a coverage map, leave it without one.
    scored = route != "deprioritized" or not ((draft.get("coverage") or {}).get("deferred") or draft.get("l3") is False)
    f = fit(reqs) if scored else None
    if policy in evaluation.POLICIES and scored:
        calculated = evaluation.assess(reqs, draft.get("adjustment", 0), draft.get("adjustment_reason"), policy)
        job.update(calculated)
        f = calculated["functional_fit"]
    elif policy in evaluation.POLICIES and draft.get("adjustment", 0):
        raise ValueError("screened-out jobs have no fit to adjust")
    job.update(fit_percent=f, functional_fit=f)
    mand = [r for r in reqs if r.get("kind") != "condition" and r.get("mandatory") is True]
    conds = [r for r in reqs if r.get("kind") == "condition"]
    if route == "deprioritized":
        job["status"] = "deprioritized"
        if not scored:
            job.update(eligibility=None, application_confidence=None, confidence_reason=None, card=None)
        else:
            job["eligibility"] = "unresolved"
        return job
    passed = all(r.get("qualification_status") == "supported" for r in mand) and \
        all(c.get("condition_status") == "pass" for c in conds)
    job["eligibility"] = "pass" if passed else "unresolved"
    job["status"] = "eligible" if passed else "needs_verification"
    return job


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assemble(run_dir, criteria_path="career/search-criteria.yaml"):
    """run.json from the manifest and the per-job results, in manifest order (missing results are left out)."""
    run_dir = Path(run_dir)
    m = load_json(run_dir / "manifest.json")
    jobs = [load_json(run_dir / e["result_file"]) for e in m["jobs"] if (run_dir / e["result_file"]).exists()]
    return {"schema_version": "1.3", "run_id": m["run_id"], "run_date": m["run_date"], "source_commit": m["source_commit"],
            **({"evaluation_policy": m["evaluation_policy"]} if m.get("evaluation_policy") else {}),
            **({"workflow_version": 2, "l1_rules": m["l1_rules"]} if "l1_rules" in m else {}),
            "search_criteria": criteria_path, "discovered_count": m["discovered"], "duplicate_count": m["duplicates"],
            "overrides": [], "jobs": jobs}


def status(run_dir, known_ids=None, expect=None):
    """complete | partial | failed, with every problem listed. The agent's narrative never sets this.
    partial: work is missing (a planned search not run, a job without a result, fewer jobs than the target).
    failed: work is wrong (invalid results, hash or ID mismatches, unexpected statuses in a regression)."""
    run_dir = Path(run_dir)
    partial, failed = [], []
    if not (run_dir / "manifest.json").exists():
        return {"status": "failed", "problems": ["manifest.json missing: run pipeline.py freeze after intake"]}
    m = load_json(run_dir / "manifest.json")
    if not m.get("frozen_input"):
        if not (run_dir / "plan.json").exists():
            failed.append("plan.json missing: run pipeline.py plan before searching")
        else:
            pl = load_json(run_dir / "plan.json")
            log = {e.get("id"): e for e in (load_json(run_dir / "search_log.json")["searches"]
                                            if (run_dir / "search_log.json").exists() else [])}
            if (run_dir / "search_log.json").exists():
                for extra in load_json(run_dir / "search_log.json").get("extra", []):
                    if extra.get("status") == "unresolved":
                        partial.append(f"unresolved extra search response: {extra.get('reason', 'unknown format')}")
            planned = {x["id"] for x in pl["searches"]}
            for sid in sorted(planned - set(log)):
                partial.append(f"search {sid} not logged")
            for sid, e in sorted(log.items()):
                if sid not in planned:
                    failed.append(f"search_log has unplanned search {sid}")
                elif e.get("status") != "run":
                    partial.append(f"search {sid} {e.get('status')}: {e.get('reason') or 'no reason given'}")
            if pl.get("target_cards"):
                prog = card_progress(run_dir)
                if not (prog["target_met"] or prog["pool_exhausted"] or prog["cap_reached"]):
                    partial.append(f"{prog['line']}; run pipeline.py top-up to fetch the next batch")
            elif len(m["jobs"]) < pl["target_unique_jobs"]:
                partial.append(f"{len(m['jobs'])} of {pl['target_unique_jobs']} target jobs in the manifest")
            if pl.get("workflow_version") == 2 and not m.get("l1_rules"):
                failed.append("current run has no pinned L1 rules; freeze using the current CLI")
            if (run_dir / "candidates.json").exists():
                candidate_doc = load_json(run_dir / "candidates.json")
                chosen = candidate_doc["selected"]
                if pl.get("workflow_version") == 2:
                    log_doc = load_json(run_dir / "search_log.json") if (run_dir / "search_log.json").exists() else {"searches": []}
                    crit = candidate_doc.get("selection_criteria", pl.get("criteria", {}))
                    if candidate_doc.get("plan_sha256") != object_hash(pl) or candidate_doc.get("search_log_sha256") != object_hash(log_doc):
                        failed.append("candidate selection inputs changed; regenerate candidates")
                    elif candidates(pl, log_doc, crit, m["run_date"], candidate_doc.get("target"))["selected"] != chosen:
                        failed.append("selected candidates differ from deterministic selection")
                bare = lambda x: x.split(":", 1)[-1]
                have = {bare(e["id"]): e["id"] for e in m["jobs"]}
                fetched = set(have) | {bare(a) for e in m["jobs"] for a in e.get("aliases", [])}
                for jid in chosen:
                    if jid not in fetched:
                        partial.append(f"candidate {jid} was not fetched")
                for jid in sorted(set(have) - set(chosen)):
                    failed.append(f"{have[jid]} is in the manifest but was not a selected candidate")
            elif pl.get("workflow_version") == 2:
                partial.append("candidates.json missing")
    listed = {e["result_file"] for e in m["jobs"]}
    if (run_dir / "jobs.json").exists():
        partial.extend(f"detail intake unresolved: {e}" for e in load_json(run_dir / "jobs.json").get("intake_errors", []))
    for f in sorted((run_dir / "results").glob("*.json")) if (run_dir / "results").exists() else []:
        if f"results/{f.name}" not in listed:
            failed.append(f"results/{f.name} is not in the manifest")
    done = 0
    for e in m["jobs"]:
        path = run_dir / e["result_file"]
        if not path.exists():
            partial.append(f"{e['id']}: no result")
            continue
        job = load_json(path)
        if job.get("id") != e["id"]:
            failed.append(f"{e['result_file']}: id {job.get('id')} does not match the manifest ({e['id']})")
            continue
        if (job.get("jd_artifact") or {}).get("canonical_sha256") != e.get("canonical_sha256"):
            failed.append(f"{e['id']}: posting hash differs from the manifest")
        errs = check_job(job, m["run_date"], known_ids, run_dir / "artifacts" if m.get("evaluation_policy") else None)
        if m.get("l1_rules"):
            intake_path = run_dir / "jobs.json"
            bases = {j["id"]: j for j in load_json(intake_path)["jobs"]} if intake_path.exists() else {}
            base = bases.get(e["id"])
            if base is None or object_hash(base) != e.get("input_sha256"):
                errs.append(f"{e['id']}: posting inputs changed or missing after freeze")
            else:
                errs.extend(enforce_l1(job, base, m, run_dir / "artifacts"))
                if any(job.get(k) != base.get(k) for k in BASE_FIELDS if k in base):
                    errs.append(f"{e['id']}: result posting fields differ from intake")
        failed.extend(errs)
        done += not errs
    if expect:
        statuses = {e["id"]: load_json(run_dir / e["result_file"]).get("status")
                    for e in m["jobs"] if (run_dir / e["result_file"]).exists()}
        for jid, allowed in expect.get("jobs", {}).items():
            if jid in statuses and statuses[jid] not in allowed:
                failed.append(f"{jid}: status {statuses.get(jid)} not in expected {allowed}")
    if not partial and not failed:
        failed.extend(validate(assemble(run_dir), run_dir / "artifacts" if m.get("l1_rules") else None, known_ids=known_ids))
    state = "failed" if failed else "partial" if partial else "complete"
    progress = card_progress(run_dir) if (run_dir / "plan.json").exists() and \
        load_json(run_dir / "plan.json").get("target_cards") else None
    return {"status": state, "jobs": len(m["jobs"]), "valid_results": done, "problems": failed + partial,
            **({"cards": progress} if progress else {}),
            "verification": "L1 enforced" if m.get("l1_rules") else "legacy structural checks; L1 not pinned"}


USAGE = """Usage:
  pipeline.py validate  <run.json> [--artifacts DIR]
  pipeline.py summarize <run.json>
  pipeline.py review    <run.json> [--all]          review order with gap names; hidden jobs only with --all
  pipeline.py cards     <run.json> [-o FILE]        render the review page (schema 1.3)
  pipeline.py decide    <run.json> <decisions.json>  copy Pass/Interested choices into the run (in place)
  pipeline.py export    <run.json> [--artifacts DIR] -o application_queue.json   handoff: Interested jobs with posting text
  pipeline.py screen    <jobs.json> [--artifacts DIR] [--profile FILE] [--criteria FILE] [--run-date YYYY-MM-DD] [-o screen.jsonl]
                                                    L1 hard gates
  pipeline.py check-profile [--profile FILE]
Run control (a run folder holds plan.json, search_log.json, jobs.json, manifest.json, results/):
  pipeline.py plan    [--criteria FILE] [--target N] -o plan.json     the searches; N is the number of review cards
  pipeline.py candidates <run dir> [--run-date DATE] [--target N]    which jobs to fetch first (writes candidates.json)
  pipeline.py top-up  <run dir>                                      after a batch is evaluated: the next jobs to fetch,
                                                                     or why the run is done (card target, pool, cap)
  pipeline.py freeze  <jobs.json> --run-id ID --run-date DATE --commit SHA [--frozen] [--add] -o manifest.json
                                       --add appends a top-up batch to an existing manifest
  pipeline.py result  <draft.json> --run-dir DIR                      build, write and check one results/<job>.json
  pipeline.py check-job <result.json> --run-date DATE                validate one job's result
  pipeline.py status  <run dir> [--expect expected.json]             complete | partial | failed (exit 0 only if complete)
  pipeline.py assemble <run dir> -o run.json                         run file with the status embedded as completion"""


def take(args, flag):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
        return value, True
    return None, False


def main():
    args = sys.argv[1:]
    artifacts_dir, has_art = take(args, "--artifacts")
    profile_path, has_profile = take(args, "--profile")
    criteria_path, has_criteria = take(args, "--criteria")
    run_date, has_date = take(args, "--run-date")
    out_path, has_out = take(args, "-o")
    target, _ = take(args, "--target")
    run_id, _ = take(args, "--run-id")
    commit, _ = take(args, "--commit")
    expect_path, _ = take(args, "--expect")
    frozen = "--frozen" in args
    raw_args = list(args)
    args = [a for a in args if a not in {"--frozen", "--add"}]
    show_all = "--all" in args
    args = [a for a in args if a != "--all"]
    if any(flag and not value for flag, value in ((has_art, artifacts_dir), (has_profile, profile_path),
                                                  (has_criteria, criteria_path), (has_date, run_date),
                                                  (has_out, out_path))) or not args:
        print(USAGE, file=sys.stderr)
        return 2
    if args[0] == "check-profile" and len(args) == 1:
        errors, warnings = check_profile(load_yaml(profile_path or DEFAULT_PROFILE))
        for w in warnings:
            print("WARNING:", w, file=sys.stderr)
        for e in errors:
            print("ERROR:", e, file=sys.stderr)
        if not errors:
            print("PASS: capability profile record IDs resolve")
        return 1 if errors else 0
    def emit(obj):
        text = json.dumps(obj, indent=1, ensure_ascii=False) + "\n"
        if out_path:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    if args[0] == "plan" and len(args) == 1:
        try:
            emit(plan(load_yaml(criteria_path or DEFAULT_CRITERIA), target=int(target) if target else None))
        except ValueError as e:
            print(f"plan: {e}", file=sys.stderr)
            return 1
        return 0
    if args[0] == "candidates" and len(args) == 2:
        rd = Path(args[1])
        result = candidates(load_json(rd / "plan.json"), load_json(rd / "search_log.json"),
                            load_yaml(criteria_path or DEFAULT_CRITERIA),
                            run_date or datetime.date.today().isoformat(), int(target) if target else None)
        dest = Path(out_path) if out_path else rd / "candidates.json"
        dest.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"wrote": str(dest), **result["counts"]}))
        return 0 if result["selected"] else 1
    if args[0] == "freeze" and len(args) == 2:
        if not (run_id and run_date and commit and re.fullmatch(r"[a-f0-9]{40}", commit)):
            print("freeze needs --run-id, --run-date and a 40-character --commit", file=sys.stderr)
            return 2
        if out_path and Path(out_path).exists():
            if "--add" not in raw_args:
                print("freeze refuses to overwrite a manifest; use a new run folder, or --add for a top-up batch",
                      file=sys.stderr)
                return 1
            manifest = load_json(out_path)
            if manifest["run_id"] != run_id or manifest["source_commit"] != commit:
                print("freeze --add must use the run's own --run-id and --commit", file=sys.stderr)
                return 1
            try:
                added = add_batch(manifest, load_json(args[1]))
            except ValueError as e:
                print(f"ERROR: {e}", file=sys.stderr); return 1
            Path(out_path).write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps({"added": added, "jobs": len(manifest["jobs"])}))
            return 0
        criteria = load_yaml(criteria_path or DEFAULT_CRITERIA)
        rules = {"conditions": criteria["conditions"],
                 "max_age_days": criteria["search"].get("max_posting_age_days"),
                 "min_pay": criteria.get("compensation", {}).get("minimum_annual_usd"),
                 "stale_after_days": criteria["search"].get("stale_after_days")}
        manifest = freeze(load_json(args[1]), run_id, run_date, commit, frozen, rules)
        manifest["evaluation_policy"] = evaluation.POLICY
        emit(manifest)
        return 0
    run_dir, _ = take(args, "--run-dir")
    if args[0] == "result" and len(args) == 2:
        if not run_dir:
            print("result needs --run-dir", file=sys.stderr)
            return 2
        draft, rd = load_json(args[1]), Path(run_dir)
        base = {j["id"]: j for j in load_json(rd / "jobs.json")["jobs"]}.get(draft.get("id"))
        if base is None:
            print(f"ERROR: {draft.get('id')} is not in {rd / 'jobs.json'}", file=sys.stderr)
            return 1
        manifest = load_json(rd / "manifest.json") if (rd / "manifest.json").exists() else None
        if manifest is None:
            print("ERROR: freeze first; result needs manifest.json", file=sys.stderr)
            return 1
        frozen_job = next((e for e in manifest["jobs"] if e["id"] == base["id"]), None)
        if frozen_job is None or (frozen_job.get("input_sha256") and frozen_job["input_sha256"] != object_hash(base)):
            print("ERROR: job inputs differ from the frozen manifest", file=sys.stderr)
            return 1
        if manifest.get("l1_rules"):
            receipt = l1_check(base, manifest["l1_rules"], manifest["run_date"], rd / "artifacts")
            if receipt["l1"] == "evaluation_error":
                draft = {"id": base["id"], "status": "evaluation_error", "error_reason": "; ".join(receipt["reasons"])}
            elif receipt["l1"] == "fail":
                draft = {"id": base["id"], "status": "excluded", "confidence_reason": "L1 condition conflict",
                         "exclusion": {"basis": "explicit_condition", "requirement_quote": str({k: base.get(k) for k in ("location", "workplace", "compensation")}),
                                       "source": "provider_metadata", "reason": "; ".join(receipt["reasons"])}}
        try:
            rules = manifest.get("l1_rules") or {}
            job = build_result(draft, base, manifest.get("evaluation_policy"), manifest.get("run_date"),
                               rules.get("stale_after_days"))
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr); return 1
        if manifest.get("l1_rules"):
            job["l1"] = receipt
            if receipt["l1"] == "unknown" and job["status"] == "eligible":
                job.update(status="needs_verification", eligibility="unresolved")
        dest = rd / "results" / f"{safe_name(job['id'])}.json"
        run_day = load_json(rd / "manifest.json")["run_date"] if (rd / "manifest.json").exists() else run_date
        errs = check_job(job, run_day, career_ids(), rd / "artifacts" if manifest.get("evaluation_policy") else None) if run_day else ["no run date: freeze first or pass --run-date"]
        errs.extend(enforce_l1(job, base, manifest, rd / "artifacts"))
        if manifest.get("l1_rules"):
            for ask in job["requirements"]:
                if ask.get("mandatory") and (ask.get("mandatory_basis") != "explicit" or ask.get("kind") == "do"):
                    errs.append("mandatory asks need explicit posting basis; responsibilities are inferred concerns")
        for e in errs:
            print("ERROR:", e, file=sys.stderr)
        if not errs:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(job, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{'PASS: wrote' if not errs else 'FAIL: did not write'} {dest} ({job['status']}, fit {job.get('fit_percent')})")
        return 1 if errs else 0
    if args[0] == "check-job" and len(args) == 2:
        if not run_date:
            print("check-job needs --run-date", file=sys.stderr)
            return 2
        errs = check_job(load_json(args[1]), run_date, career_ids(), artifacts_dir)
        for e in errs:
            print("ERROR:", e, file=sys.stderr)
        print("PASS" if not errs else f"FAIL: {len(errs)} error(s)")
        return 1 if errs else 0
    if args[0] == "top-up" and len(args) == 2:
        try:
            result = top_up(args[1])
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr); return 1
        emit(result)
        return 0
    if args[0] in {"status", "assemble"} and len(args) == 2:
        result = status(args[1], career_ids(), load_json(expect_path) if expect_path else None)
        if args[0] == "status":
            emit(result)
            return 0 if result["status"] == "complete" else 1
        run = assemble(args[1])
        run["completion"] = result
        emit(run)
        return 0
    if args[0] == "decide" and len(args) == 3:
        run = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        counts = apply_decisions(run, json.loads(Path(args[2]).read_text(encoding="utf-8")))
        Path(args[1]).write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"imported": True, "run_id": run.get("run_id"), "counts": counts}))
        return 0
    if args[0] == "export" and len(args) == 2:
        run = load_json(args[1])
        queue = export_queue(run, artifacts_dir)
        if not queue["choices_imported"]:
            print("WARNING: no choices imported; this queue is not the user's selection. Run pipeline.py decide with their "
                  "Download my choices file first, or ask them for it", file=sys.stderr)
        elif not queue["jobs"]:
            print("WARNING: no Interested jobs in the imported choices", file=sys.stderr)
        missing = [x["job_id"] for x in queue["jobs"] if x["posting"] is None]
        if missing:
            print(f"WARNING: no posting text for {len(missing)} job(s); pass --artifacts", file=sys.stderr)
        emit(queue)
        return 0
    if len(args) != 2 or args[0] not in {"validate", "summarize", "review", "screen", "cards"}:
        print(USAGE, file=sys.stderr)
        return 2
    run = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    if args[0] == "screen":
        criteria = load_yaml(criteria_path or DEFAULT_CRITERIA)
        conditions = criteria["conditions"]
        max_age = (criteria.get("search") or {}).get("max_posting_age_days")
        min_pay = (criteria.get("compensation") or {}).get("minimum_annual_usd")
        day = run_date or run.get("run_date") or datetime.date.today().isoformat()
        cache, lines = {}, []
        for j in run["jobs"]:
            result, reasons = screen_job(j, conditions, artifacts_dir, cache, day, max_age, min_pay)
            lines.append(json.dumps({"id": j.get("id"), "l1": result, "reasons": reasons}, ensure_ascii=False))
        text = "\n".join(lines) + "\n"
        if out_path:
            Path(out_path).write_text(text, encoding="utf-8")
            print(f"wrote {out_path}: {len(lines)} jobs")
        else:
            sys.stdout.write(text)
        return 0
    if args[0] == "review":
        for j in review_queue(run, show_all):
            fitv = j.get("functional_fit", j.get("fit_percent"))
            gaps = (j.get("screen") or {}).get("critical_gaps") or []
            print(f"{j['status']:<18} {str(j.get('eligibility')):<10} conf={str(j.get('application_confidence')):<6} "
                  f"fit={fitv}  {j['company']} · {j['title']}" + (f"  gaps: {', '.join(gaps)}" if gaps else ""))
        return 0
    if artifacts_dir is None and run.get("workflow_version") == 2:
        artifacts_dir = Path(args[1]).parent / "artifacts"
    errors = validate(run, artifacts_dir, career_ids())
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    if args[0] == "cards":
        page = render_cards(run)
        if out_path:
            Path(out_path).write_text(page, encoding="utf-8")
            print(f"wrote {out_path}: {len(card_data(run)['cards'])} cards")
        else:
            sys.stdout.write(page)
        return 0
    if args[0] == "validate":
        print("PASS: run accounting, scoring and provenance checks")
        verified = sum(r.get("quote_status") == "source_verified" for j in run["jobs"] for r in j["requirements"])
        if artifacts_dir:
            missing = quote_warnings(run, artifacts_dir)
            for w in missing:
                print("WARNING:", w, file=sys.stderr)
            print(f"{'WARN' if missing else 'PASS'}: {len(missing)} quote(s) not found in the posting text")
        if verified:
            print(f"PASS: {verified} source-verified requirement quote(s) checked against JD artifacts")
    else:
        print(json.dumps(summary(run), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

