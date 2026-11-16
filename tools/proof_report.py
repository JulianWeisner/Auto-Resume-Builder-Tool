#!/usr/bin/env python3
"""Proof report: one readable page that shows whether a built résumé can be trusted.

Usage:
    python3 tools/proof_report.py RESUME-snapshot/ [--out proof.html]

Assembled from the build snapshot by script, with no agent writing, when the
user asks for a "proof report". Sections:
  1. Claim sources: each résumé line from sources.md, the records it names and
     each record's current wording and limitations (when the career records
     are on disk; otherwise the IDs alone).
  2. Fact confirmations: the plan's Review before build and title lines.
  3. Term evidence: each job term, the requirement it comes from and how the
     check found it.
  4. Automatic check: the full readability and voice results.
  5. Sources and build log: the plan's source line, tool versions, file hashes.

The reasoning behind the résumé (story choices, storyboard, gaps) is the
separate reasoning report, written by the agent on request.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ID = re.compile(r"(?<![\w-])[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*-\d{2,4}(?![\w-])")


def find_ids(text, records):
    """Record IDs named in text, in order: known IDs when the records are on disk, else ID-shaped tokens."""
    if records:
        hits = {m.start(): rid for rid in records
                for m in re.finditer(rf"(?<![\w-]){re.escape(rid)}(?![\w-])", text)}
        for m in ID.finditer(text):  # ID-shaped but unknown: show it as not found
            if not any(k <= m.start() < k + len(r) for k, r in hits.items()):
                hits[m.start()] = m.group(0)
        return [hits[k] for k in sorted(hits)]
    return ID.findall(text)


def esc(text):
    return html.escape(str(text))


def excerpt(text, limit=320):
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def load_records():
    """Career records by ID, or {} when the repository's records are not on disk."""
    try:
        sys.path.insert(0, str(TOOLS))
        import current_view
        return {r["id"]: r for p in current_view.COLLECTIONS
                if (current_view.ROOT / p).is_file() for r in current_view.records(p)}
    except (ImportError, SystemExit, OSError):
        return {}


def read(folder, name):
    path = folder / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def plan_lines(plan, prefix):
    return [l.split(":", 1)[1].strip() for l in plan.splitlines()
            if l.lstrip("- ").lower().startswith(prefix.lower())]


def claim_section(sources, records):
    rows = []
    for line in sources.splitlines():
        line = line.strip().lstrip("-* ").strip()
        if not line:
            continue
        parts = re.split(r"\s*(?:->|→)\s*", line, maxsplit=1)
        claim, refs = (parts[0], parts[1]) if len(parts) == 2 else (line, line)
        ids = find_ids(refs, records)
        cells = []
        for rid in ids:
            rec = records.get(rid)
            if not rec:
                cells.append(f"<div class='rec'><b>{esc(rid)}</b> <span class='muted'>"
                             f"{'record not found' if records else 'records not on disk'}</span></div>")
                continue
            wording = rec.get("current_account") or rec.get("current_interpretation") or ""
            limits = [str(x) for k in ("limitations", "scope_and_status") for x in (rec.get(k) or [])]
            cells.append(f"<div class='rec'><b>{esc(rid)}</b> · {esc(rec.get('title', ''))}"
                         + (f"<div>{esc(excerpt(wording))}</div>" if wording else "")
                         + (f"<div class='limit'>Limits: {esc(excerpt(limits[0], 200))}"
                            + (f" (+{len(limits) - 1} more)" if len(limits) > 1 else "") + "</div>" if limits else "")
                         + "</div>")
        if not ids:
            cells.append("<span class='bad'>no record named</span>")
        rows.append(f"<tr><td>{esc(claim)}</td><td>{''.join(cells)}</td></tr>")
    if not rows:
        return "<p class='muted'>No sources.md in this snapshot.</p>"
    return "<table><tr><th>Résumé line</th><th>Records and their current wording</th></tr>" + "".join(rows) + "</table>"


def terms_section(check, tags):
    part2 = check.split("Part 2", 1)[1] if "Part 2" in check else ""
    rows = []
    for line in part2.splitlines():
        m = re.match(r"\s+(PASS|OUT|FAIL)\s+(\S+)\s+(.*)", line)  # term rows are indented
        if not m:
            continue
        status, tag, rest = m.groups()
        quote = (tags.get(tag) or {}).get("text", "")
        label = {"PASS": "covered", "OUT": "no evidence, left out", "FAIL": "missing"}[status]
        rows.append(f"<tr><td class='{status.lower()}'>{label}</td><td>{esc(rest)}</td>"
                    f"<td><b>{esc(tag)}</b> {esc(excerpt(quote, 220))}</td></tr>")
    if not rows:
        return "<p class='muted'>No job terms were checked for this résumé.</p>"
    return "<table><tr><th>Status</th><th>Term and how it was found</th><th>From the posting</th></tr>" + "".join(rows) + "</table>"


def check_section(check):
    part1 = check.split("Part 2", 1)[0]
    rows = []
    for line in part1.splitlines():
        m = re.match(r"\s*(PASS|WARN|FAIL)\s+(.*)", line)
        if m:
            label, _, detail = m[2].partition(": ")
            rows.append(f"<tr><td class='{m[1].lower()}'>{m[1]}</td><td>{esc(label)}</td><td>{esc(detail)}</td></tr>")
    summary = next((l for l in reversed(check.splitlines()) if l.startswith(("PASS", "FAIL"))), "")
    return (f"<p><b>{esc(summary)}</b></p>" if summary else "") + \
        ("<table><tr><th></th><th>Check</th><th>Detail</th></tr>" + "".join(rows) + "</table>" if rows else "")


def build(folder):
    manifest = json.loads(read(folder, "manifest.json") or "{}")
    plan = read(folder, "plan.md")
    check = next((read(folder, p.name) for p in folder.glob("*.check.txt")), "")
    try:
        tags = json.loads(read(folder, "tags.json") or "{}")
    except json.JSONDecodeError:
        tags = {}
    records = load_records()
    confirmations = plan_lines(plan, "review before build") + plan_lines(plan, "titles")
    source = plan_lines(plan, "source")
    tools = manifest.get("tools", {})
    files = manifest.get("files", {})
    pdf = next((n for n in files if n.endswith(".pdf")), folder.name)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Proof report · {esc(pdf)}</title>
<style>
:root {{ --fg:#1b1b1b; --muted:#666; --line:#ddd; --bg:#fff; --ok:#1a7f37; --warn:#9a6700; --bad:#cf222e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg:#e6e6e6; --muted:#9a9a9a; --line:#333; --bg:#111;
  --ok:#3fb950; --warn:#d29922; --bad:#f85149; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 -apple-system, system-ui, Arial, sans-serif;
  max-width:980px; margin:0 auto; padding:24px 16px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; border-bottom:1px solid var(--line); padding-bottom:4px; }}
table {{ width:100%; border-collapse:collapse; }} th, td {{ text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--line); }}
th {{ font-size:13px; color:var(--muted); font-weight:600; }} .rec + .rec {{ margin-top:8px; }}
.muted, .limit {{ color:var(--muted); font-size:13px; }} .pass {{ color:var(--ok); font-weight:600; }}
.warn, .out {{ color:var(--warn); font-weight:600; }} .fail, .bad {{ color:var(--bad); font-weight:600; }}
code {{ font-size:12px; word-break:break-all; }} @media (max-width:640px) {{ table, tr, td, th {{ display:block; }} th {{ display:none; }} td {{ border:0; padding:2px 0; }} tr {{ border-bottom:1px solid var(--line); padding:8px 0; }} }}
</style></head><body>
<h1>Proof report</h1>
<p class="muted">{esc(pdf)} · built {esc(manifest.get('built_at', 'time unknown'))} · assembled from the build snapshot by script; the reasoning behind choices is in the reasoning report.</p>
<h2>1. Claim sources</h2>{claim_section(read(folder, 'sources.md'), records)}
<h2>2. Fact confirmations</h2>{"<ul>" + "".join(f"<li>{esc(c)}</li>" for c in confirmations) + "</ul>" if confirmations else "<p class='muted'>None recorded in plan.md.</p>"}
<h2>3. Term evidence</h2>{terms_section(check, tags)}
<h2>4. Automatic check</h2>{check_section(check) or "<p class='muted'>No check output in this snapshot.</p>"}
<h2>5. Sources and build log</h2><ul>
{"".join(f"<li>{esc(s)}</li>" for s in source) or "<li class='muted'>No source line in plan.md.</li>"}
{"".join(f"<li>{esc(k)}: {esc(v)}</li>" for k, v in tools.items())}
</ul><table><tr><th>File</th><th>SHA-256</th></tr>{"".join(f"<tr><td>{esc(n)}</td><td><code>{esc(h)}</code></td></tr>" for n, h in files.items())}</table>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser(description="Proof report from a build snapshot (see module docstring).")
    ap.add_argument("snapshot")
    ap.add_argument("--out", help="output file (default: proof.html inside the snapshot)")
    a = ap.parse_args()
    folder = Path(a.snapshot)
    if not (folder / "manifest.json").is_file():
        ap.error(f"not a build snapshot (no manifest.json): {folder}")
    out = Path(a.out) if a.out else folder / "proof.html"
    out.write_text(build(folder), encoding="utf-8")
    print(f"Proof report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
