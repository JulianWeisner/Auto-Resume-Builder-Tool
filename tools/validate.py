#!/usr/bin/env python3
"""Validate your career repository. Read-only; exits 1 if any check fails.

Run after every information update. Checks:
  - YAML frontmatter and every fenced YAML record parse
  - record IDs are unique and each has its lowercase anchor (<a id="...">)
  - no unfinished template placeholders ({like this}) in records
  - relationship targets exist and backlinks are reciprocal
  - functions and capabilities are registered in career/vocabulary.md
  - "## ID — Title" headings match their record's title
  - CV source lines resolve in the snapshot named by source_revision
  - no section label stored as an account
  - relative links and anchors resolve
  - every agent module is routed from AGENTS.md and says when to load it

career/_templates/ and application archives are not parsed as records.
An empty skeleton passes.

Requires Python 3 and PyYAML (pip install pyyaml).

Usage: python3 tools/validate.py
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VOCAB = ROOT / "career/vocabulary.md"
SNAPSHOT_DIR = ROOT / "source-material/cv"
REL_KEYS = ["associated_roles", "associated_projects", "outcomes", "associated_experiences",
            "related_experiences", "formal_title_ids", "functional_role_ids"]
PLACEHOLDER = re.compile(r"\{[^{}\"]{1,80}\}")
YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.S)
errors = []


def err(*a):
    errors.append(" ".join(str(x) for x in a))


def rel(p):
    return p.relative_to(ROOT).as_posix()


def slug(heading):
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def is_template(p):
    return rel(p).startswith("career/_templates/")


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


# Archive payloads are historical data, not records or citations; check only the README.
md_files = sorted(
    p for p in ROOT.rglob("*.md")
    if ".git" not in p.parts
    and (p.relative_to(ROOT).parts[0] != "applications" or p == ROOT / "applications/README.md")
)
texts = {p: p.read_text(encoding="utf-8") for p in md_files}

# Parse records
anchors, records = {}, {}
for p, t in texts.items():
    anchors[p] = set(re.findall(r'<a id="([^"]+)"', t)) | {slug(h) for h in re.findall(r"^#+\s+(.*)$", t, re.M)}
    if t.startswith("---\n"):
        try:
            yaml.safe_load(t.split("---\n")[1])
        except yaml.YAMLError as e:
            err("frontmatter", rel(p), e)
    if is_template(p) or not rel(p).startswith("career/"):
        continue
    fm_rev = re.search(r'^source_revision: "(\w+)"', t, re.M)
    for i, block in enumerate(YAML_BLOCK.findall(t)):
        try:
            d = yaml.safe_load(block)
        except yaml.YAMLError as e:
            err("yaml", rel(p), "block", i + 1, e)
            continue
        if not (isinstance(d, dict) and "id" in d):
            continue
        rid = str(d["id"])
        if rid in records:
            err("duplicate id", rid, rel(p), "and", rel(records[rid][0]))
        if rid.lower() not in anchors[p]:
            err("missing anchor", rid, rel(p), f'(add <a id="{rid.lower()}"></a> above the block)')
        for s in strings(d):
            m = PLACEHOLDER.search(s)
            if m and not s.lstrip().startswith(("{\"", "[")):
                err("unfinished placeholder", rid, m.group(0))
                break
        if PLACEHOLDER.fullmatch(rid):
            err("unfinished placeholder", rid)
        d.setdefault("_rev", fm_rev.group(1) if fm_rev else None)
        records[rid] = (p, d)

ids = set(records)

# Relationships and backlinks
for rid, (p, d) in records.items():
    for k in REL_KEYS:
        for ref in d.get(k) or []:
            if isinstance(ref, str) and ref not in ids:
                err("dangling", rid, k, ref)


def linked(rid, key):
    return set(records[rid][1].get(key) or [])


for rid, (p, d) in records.items():
    if d.get("record_type") == "experience":
        for r in d.get("associated_roles") or []:
            if r in ids and "associated_experiences" in records[r][1] and rid not in linked(r, "associated_experiences"):
                err("role backlink missing", r, rid)
        for o in d.get("outcomes") or []:
            if o in ids and rid not in linked(o, "associated_experiences"):
                err("outcome backlink missing", o, rid)
        for pr in d.get("associated_projects") or []:
            if pr in ids and rid not in linked(pr, "associated_experiences"):
                err("project backlink missing", pr, rid)
    for e in d.get("associated_experiences") or []:
        if e in ids:
            ed = records[e][1]
            back = set((ed.get("associated_roles") or []) + (ed.get("outcomes") or []) + (ed.get("associated_projects") or []))
            if rid not in back:
                err("stale backlink", rid, "->", e)

# One vocabulary: every function and capability is a registered tag
vocab_text = re.sub(r"<!--.*?-->", "", VOCAB.read_text(encoding="utf-8"), flags=re.S) if VOCAB.exists() else ""
vocab = set(re.findall(r"^\s*-\s+\*\*((?:FN|CAP)-[\w-]+)\*\*", vocab_text, re.M))
for rid, (p, d) in records.items():
    for key, prefix in (("functions", "FN-"), ("capabilities", "CAP-")):
        for tag in d.get(key) or []:
            if tag not in vocab:
                hint = "" if str(tag).startswith(prefix) else f" (use a registered {prefix} tag)"
                err("unregistered tag", rid, key, repr(tag) + hint, "→ add it to career/vocabulary.md")

# Headings of the form "## ID — Title" match the record below them
for p, t in texts.items():
    if is_template(p) or not rel(p).startswith("career/"):
        continue
    for m in re.finditer(r"^#{2,3} (\S+) — (.+)\n(?:\s*\n)*```yaml\n(.*?)```", t, re.M | re.S):
        try:
            d = yaml.safe_load(m.group(3))
        except yaml.YAMLError:
            continue
        if isinstance(d, dict) and d.get("id") == m.group(1) and d.get("title") and d["title"] != m.group(2).strip():
            err("heading title differs from YAML", m.group(1), rel(p))

# CV source lines resolve against the snapshot named by their revision
snapshots = {}
for snap in SNAPSHOT_DIR.glob("Curriculum-Vitae.*.md"):
    snapshots[snap.name.split(".")[1]] = snap.read_text(encoding="utf-8").splitlines()
for rid, (p, d) in records.items():
    lines = d.get("source_lines") or []
    rev = str(d.get("source_revision") or d.get("_rev") or "")
    if not lines or not rev:
        continue
    snap = next((v for k, v in snapshots.items() if rev.startswith(k)), None)
    if snap is None:
        err("no CV snapshot for source_revision", rid, rev[:7], "(expected source-material/cv/Curriculum-Vitae.<short-sha>.md)")
        continue
    for n in lines:
        if not (1 <= n <= len(snap)) or not snap[n - 1].strip():
            err("source line missing or blank in snapshot", rid, n)

# Section labels imported as accounts
for rid, (p, d) in records.items():
    acc = d.get("current_account")
    if isinstance(acc, str) and acc.strip().endswith(":") and len(acc) < 60:
        err("section label stored as account", rid, repr(acc))

# Relative links and anchors (templates hold links written for their copy destination)
for p, t in texts.items():
    if is_template(p):
        continue
    for m in re.finditer(r"\]\(([^)\s]+)\)", t):
        url = m.group(1)
        if url.startswith(("http", "mailto")) or "{" in url:
            continue
        path, _, anchor = url.partition("#")
        target = (p.parent / path).resolve() if path else p
        if not target.exists():
            err("broken link", rel(p), url)
        elif anchor and target.suffix == ".md" and anchor not in anchors.get(target, set()):
            err("missing anchor", rel(p), url)

# Agent guide routing: every module is routed from AGENTS.md and says when to load it
core = (ROOT / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "AGENTS.md").is_file() else ""
routing = core.split("## Routing", 1)[1].split("\n## ", 1)[0] if "## Routing" in core else ""
if (ROOT / "agents").exists():
    if not routing:
        err("AGENTS.md has no Routing section")
    routed = {(ROOT / u.split("#")[0]).resolve() for u in re.findall(r"\]\(([^)\s]+)\)", routing)}
    for p in sorted((ROOT / "agents").rglob("*.md")):
        if p.resolve() not in routed:
            err("agent module not routed from AGENTS.md", rel(p))
        if "**Load when:**" not in texts.get(p, ""):
            err("agent module missing 'Load when' line", rel(p))

if errors:
    print("\n".join(errors))
    print(f"FAILED: {len(errors)} problem(s) across {len(records)} records")
    sys.exit(1)
print(f"OK: {len(records)} records, {len(vocab)} vocabulary tags, {len(md_files)} Markdown files")
