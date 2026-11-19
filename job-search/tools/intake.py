"""Format adapters and validation for saved provider responses (standard library only).

Original responses stay authoritative. Unknown formats raise IntakeError rather than
becoming empty searches. Add adapters/fixtures without removing existing formats.
"""
import datetime
import json
import re
from urllib.parse import parse_qs, urlparse


class IntakeError(ValueError):
    pass


def unpack(value):
    if isinstance(value, str):
        try:
            return unpack(json.loads(value))
        except json.JSONDecodeError:
            return value
    if not isinstance(value, dict):
        raise IntakeError("unsupported response: expected text or an object")
    if value.get("isError"):
        raise IntakeError("provider returned an error")
    structured = value.get("structuredContent")
    if isinstance(structured, dict) and ("jobs" in structured or "job" in structured):
        return structured
    if "jobs" in value or "job" in value:
        return value
    if "id" in value and "description" in value:
        return value
    content = value.get("content")
    if isinstance(content, list):
        text = "\n".join(x.get("text", "") for x in content if x.get("type") == "text")
        if text:
            return unpack(text)
    raise IntakeError("unrecognized response envelope; original retained")


def required(obj, key):
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise IntakeError(f"missing or invalid {key}")
    return v


def date(value):
    if value is None or value == "":
        return None
    try:
        result = str(value)[:10]
        datetime.date.fromisoformat(result)
        return result
    except ValueError as e:
        raise IntakeError(f"invalid posting date {value!r}") from e


def search(value):
    payload = unpack(value)
    reported, returned = None, {}
    if isinstance(payload, dict):
        rows = payload.get("jobs")
        if not isinstance(rows, list):
            raise IntakeError("search response has no jobs array")
        reported = payload.get("count")
        items = []
        for row in rows:
            if not isinstance(row, dict):
                raise IntakeError("invalid job entry")
            items.append({"job_id": required(row, "id"), "title": required(row, "title"),
                          "company": required(row, "company"), "posted_date": date(row.get("datePosted")),
                          "location": row.get("location"), "workplace": row.get("workplaceType"),
                          "url": row.get("applyUrl") or row.get("url")})
        returned = {k: payload[k] for k in ("active_filters", "search_request", "full_results_url") if k in payload}
        fmt = "structured-jobs"
    else:
        if not payload.startswith("## HiringCafe job results"):
            raise IntakeError("unrecognized search text; no jobs is not a verified empty result")
        items = []
        blocks = re.split(r"^### ", payload, flags=re.M)[1:]
        for block in blocks:
            head = re.match(r"\[(?P<title>.+?)\]\((?P<url>[^)]+)\)\n\*\*(?P<company>.+?)\*\*", block)
            jid = re.search(r"^- \*\*Job ID:\*\* (\S+)", block, re.M)
            if not (head and jid):
                raise IntakeError("could not parse a listing block; original retained")
            posted = re.search(r"^- \*\*Posted:\*\* ([^\n]+)", block, re.M)
            items.append({"job_id": jid[1], "title": head["title"], "company": head["company"],
                          "posted_date": date(posted[1]) if posted else None, "url": head["url"]})
        count = re.search(r"showing (\d+)\b", payload, re.I)
        reported = int(count[1]) if count else None
        explicit_empty = bool(re.search(r"\b(?:no (?:matching )?(?:jobs|results|matches)|0 (?:jobs|results|matches))\b", payload, re.I))
        if not items and reported != 0 and not explicit_empty:
            raise IntakeError("search text contains no parseable jobs or explicit empty result")
        fmt = "markdown-listings"
    if reported is not None and (type(reported) is not int or reported < 0 or reported != len(items)):
        raise IntakeError(f"count mismatch: provider reports {reported}, parsed {len(items)}")
    if len({x["job_id"] for x in items}) != len(items):
        raise IntakeError("duplicate IDs within one search response")
    return {"items": items, "reported_count": reported, "format": fmt, "returned": returned}


def compensation(pay):
    if pay is None:
        return None
    if not isinstance(pay, dict):
        raise IntakeError("invalid compensation object")
    amounts = [pay.get(k) for k in ("minimum", "maximum")]
    if any(v is not None and (type(v) not in (int, float) or v < 0) for v in amounts):
        raise IntakeError("invalid compensation amount")
    if all(v is not None for v in amounts) and amounts[0] > amounts[1]:
        raise IntakeError("compensation minimum exceeds maximum")
    # L1's legacy string parser understands USD. Other currencies remain unknown,
    # and are retained in provider_compensation rather than compared as dollars.
    if pay.get("currency") != "USD":
        return None
    units = {"Yearly": "yr", "Monthly": "mo", "Weekly": "wk", "Hourly": "hr", "Daily": "day"}
    if pay.get("frequency") not in units or pay.get("frequency") == "Daily":
        return None
    values = ["$" + f"{v:,.2f}".rstrip("0").rstrip(".") for v in amounts if v is not None]
    return " – ".join(values) + "/" + units[pay["frequency"]] if values else None


def detail(value):
    payload = unpack(value)
    if not isinstance(payload, dict):
        raise IntakeError("detail adapter expects structured data")
    row = payload.get("job", payload)
    if not isinstance(row, dict):
        raise IntakeError("job unavailable or detail response malformed")
    job = {"title": required(row, "title"), "company": required(row, "company"),
           "provider_job_id": required(row, "id"), "posting_url": required(row, "applyUrl"),
           "location": row.get("location"), "workplace": row.get("workplaceType"),
           "compensation": compensation(row.get("compensation")),
           "provider_compensation": row.get("compensation"), "posted_date": date(row.get("datePosted"))}
    description = required(row, "description")
    return job, description


def filter_checks(requested, returned):
    """Compare only exposed values; an unexposed filter is unknown, never confirmed."""
    actual = {}
    active = returned.get("active_filters", [])
    for item in active:
        actual[item.get("key")] = item.get("value")
    state = {}
    try:
        state = json.loads(parse_qs(urlparse(returned.get("full_results_url", "")).query)["searchState"][0])
    except (ValueError, KeyError, IndexError):
        pass
    if "dateFetchedPastNDays" in state:
        actual["posted_within_days"] = "fetch freshness (not posting age)"
    if state.get("seniorityLevel"):
        actual["seniority_levels"] = state["seniorityLevel"]
    if "searchQuery" in state:
        actual["search"] = state["searchQuery"]
    for loc in state.get("locations", []):
        actual.setdefault("location", loc.get("formatted_address"))
        if loc.get("workplace_types"):
            actual["workplace_types"] = loc["workplace_types"]
        if "radius" in loc.get("options", {}):
            actual["radius_miles"] = loc["options"]["radius"]
    checks = []
    normalize = lambda v: sorted(str(x).casefold().strip() for x in v) if isinstance(v, list) else str(v).casefold().strip()
    for key, want in requested.items():
        got = actual.get(key)
        # Location aliases are left for explicit inspection, not silently equated.
        checks.append({"key": key, "requested": want, "returned": got,
                       "status": "unknown" if got is None else "confirmed" if normalize(want) == normalize(got) else "changed"})
    return checks
