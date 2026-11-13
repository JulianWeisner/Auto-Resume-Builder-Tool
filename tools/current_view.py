#!/usr/bin/env python3
"""Print the current, drafting-relevant fields of every career record.

Read-only discovery and full evidence views (see AGENTS.md). Raw record files
govern factual verification and information updates.

Collections are found automatically: every Markdown file under career/ that
holds fenced YAML records, except career/_templates/.

Every YAML key must be classified below as SHOWN or OMITTED. An unclassified
key stops the script with an error, so new qualification fields cannot vanish
from this view silently.

Requires Python 3 and PyYAML (pip install pyyaml).

Usage: python3 tools/current_view.py [--file PATH ...] [--ids ID ...] [--related]
       python3 tools/current_view.py --index
       python3 tools/current_view.py --search "returns" "reverse logistics"
"""
import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # use the setup environment when it exists (build_resume.py --setup)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from resume_check import use_tool_env
    use_tool_env()
    sys.exit("current_view: PyYAML is missing. Run `python3 tools/build_resume.py --setup`, "
             "or `python3 -m pip install pyyaml`.")

ROOT = Path(__file__).resolve().parent.parent
CAREER = ROOT / "career"
YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.S)


def collections():
    """Every Markdown file under career/ with at least one YAML record, except career/_templates/.
    Add a collection folder and it appears here with no change to this script."""
    found = []
    for p in sorted(CAREER.rglob("*.md")) if CAREER.is_dir() else []:
        if "_templates" in p.relative_to(CAREER).parts:
            continue
        if YAML_BLOCK.search(p.read_text(encoding="utf-8")):
            found.append(p.relative_to(ROOT).as_posix())
    return found


COLLECTIONS = collections()
# Prose pages with user-confirmed content that is not stored as YAML records.
# Printed verbatim after the records in a full (unfiltered) view.
PROSE_PAGES = [
    "career/preferences.md",
]
# Order matters: fields print in this order.
SHOWN = [
    "id", "record_type", "title", "organization", "historical_names",
    "display_dates", "current_dates", "start", "end", "date", "date_precision", "date_note",
    "role_kind", "title_status", "title_status_verification", "relationship",
    "formal_title_ids", "functional_role_ids", "functional_window",
    "functional_labels", "functional_label_selection", "label_clarification",
    "current_status", "presentation_note", "current_team_context",
    "current_account", "current_interpretation", "measurement_period",
    "release_status", "release_context", "definition_status",
    "limitations", "current_clarifications", "scope_and_status", "evidence_notes",
    "account_basis", "verification", "tools",
    "associated_roles", "associated_projects", "outcomes",
    "associated_experiences", "related_experiences",
]
OMITTED = {
    "legacy_metadata", "legacy_claims", "legacy_linked_roles", "metadata_dates",
    "source_path", "source_revision", "source_lines", "source_visibility",
    "evidence", "visibility", "functions", "capabilities", "organization_id",
}
CONTEXT_LINKS = ("associated_roles", "formal_title_ids",
                 "outcomes", "related_experiences")


def records(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    for block in YAML_BLOCK.findall(text):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "id" in data:
            yield data


def excerpt(text, limit=200):
    text = re.sub(r"\s+", " ", str(text).replace("\\n", " ")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def month(value):
    """'2025-12' -> 'Dec 2025'; other values (present, display text) pass through."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", str(value).strip())
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}"
    return "Present" if str(value).strip().lower() == "present" else str(value)


def date_range(value):
    """Readable dates for index lines; dict windows become 'Mon YYYY - Mon YYYY'."""
    if isinstance(value, dict):
        return " - ".join(month(value[k]) for k in ("start", "end") if value.get(k))
    return str(value or "")


def limit_notes(rec, by_id):
    """Short limits note so an excerpt never appears without its qualifications.
    Own limitations and scope notes come first; otherwise name linked roles that carry limitations."""
    own = [str(x) for key in ("limitations", "scope_and_status") for x in (rec.get(key) or [])]
    if own:
        more = f" (+{len(own) - 1} more)" if len(own) > 1 else ""
        return "limits: " + excerpt(own[0], 140) + more
    roles = [rid for rid in rec.get("associated_roles") or []
             if (by_id.get(rid) or {}).get("limitations")]
    return ("limits on role: " + ", ".join(roles)) if roles else ""


def print_index(catalog, paths, queries):
    print("Story index: discovery excerpts only. Load full records with --ids ID ... --related before scoring or drafting.")
    print("An absent match is unexamined. Search the current records and check likely collections before declaring a gap.")
    print("Role dates and labels are navigation; verify functional_window and limitations in the full records.")
    print("A 'limits' note means the claim has qualifications: never use a number or outcome from an excerpt without them.")
    by_id = {rec["id"]: rec for recs in catalog.values() for rec in recs}
    for path in paths:
        print(f"\n##### {path}")
        for rec in catalog[path]:
            searchable = " ".join(str(rec.get(key, "")) for key in SHOWN)
            if queries and not any(query.casefold() in searchable.casefold() for query in queries):
                continue
            if rec.get("record_type") in ("role", "education"):
                dates = date_range(rec.get("functional_window") or rec.get("current_dates") or rec.get("display_dates")
                                   or {k: rec[k] for k in ("start", "end") if rec.get(k)})
                flag = f"limits: {len(rec['limitations'])}" if rec.get("limitations") else ""
                print(" | ".join(x for x in (rec["id"], rec.get("organization", ""), rec.get("title", ""), dates, flag) if x))
                continue
            if rec.get("record_type") not in ("experience", "credentials") and not (queries and rec.get("record_type") == "outcome"):
                continue
            account = str(rec.get("current_account") or rec.get("current_interpretation", ""))
            sentences = re.split(r"(?<=[.!?])\s+", account.replace("\\n", " "))
            lead = excerpt(sentences[0])
            # A separate result excerpt helps long accounts expose outcomes beyond their opening.
            result = next((sentence for sentence in sentences[1:]
                           if re.search(r"\d|agreement|signed|shipped|launched|delivered|adopted|grew|cut|reduced|continued|handoff", sentence, re.I)), "")
            if queries:
                result = next((sentence for sentence in sentences
                               if any(query.casefold() in sentence.casefold() for query in queries)), result)
            links = rec.get("associated_roles") or rec.get("associated_experiences") or []
            parts = [rec["id"], rec.get("title", ""), ", ".join(links), lead]
            if result and result != sentences[0]:
                parts.append(excerpt(result))
            if rec.get("release_status"):
                parts.append("release_status=" + str(rec["release_status"]))
            note = limit_notes(rec, by_id)
            if note:
                parts.append(note)
            print(" | ".join(part for part in parts if part))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", nargs="*", help="limit to these collection files")
    ap.add_argument("--ids", nargs="*", help="limit to these record IDs")
    ap.add_argument("--index", action="store_true", help="compact whole-career discovery view")
    ap.add_argument("--search", nargs="+", help="find phrases in current fields; print matching index entries")
    ap.add_argument("--related", action="store_true", help="also load linked roles, outcomes and related experiences")
    args = ap.parse_args()
    if args.ids is not None and not args.ids:
        ap.error("--ids needs at least one record ID")
    if (args.index or args.search) and (args.ids or args.related):
        ap.error("use --index or --search for discovery; use --ids with --related for evidence")
    if args.related and not args.ids:
        ap.error("--related requires --ids")
    if not COLLECTIONS:
        print("The career record has no records yet. Ask your agent to help fill it (see START.md).")
        return
    files = args.file or COLLECTIONS
    catalog = {path: list(records(path)) for path in dict.fromkeys([*COLLECTIONS, *files])}
    unknown = {key for path in files for rec in catalog[path]
               for key in set(rec) - set(SHOWN) - OMITTED}
    if unknown:
        sys.exit("current_view.py: unclassified field(s) " + ", ".join(sorted(unknown))
                 + ". Add each to SHOWN or OMITTED before relying on this view.")
    if args.index or args.search:
        print_index(catalog, files, args.search)
        return
    selected = set(args.ids or [])
    by_id = {rec["id"]: rec for path in files for rec in catalog[path]}
    if selected - by_id.keys():
        ap.error("unknown record IDs: " + ", ".join(sorted(selected - by_id.keys())))
    if args.related:
        pending = list(selected)
        while pending:
            rec = by_id[pending.pop()]
            linked = {rid for key in CONTEXT_LINKS for rid in rec.get(key) or []}
            missing = linked - by_id.keys()
            if missing:
                ap.error("linked records outside the selected collections: " + ", ".join(sorted(missing)))
            pending.extend(sorted(linked - selected))
            selected.update(linked)
    out = []
    # Long text values repeated across many records are printed once in a legend.
    counts = {}
    for path in COLLECTIONS:
        for rec in catalog[path]:
            for k, v in rec.items():
                if isinstance(v, str) and len(v) > 40:
                    counts[(k, v)] = counts.get((k, v), 0) + 1
    legend = {kv: f"[{kv[0]} default {i + 1}]" for i, kv in
              enumerate(sorted(kv for kv, n in counts.items() if n >= 5))}
    for path in files:
        out.append(f"\n##### {path}\n")
        for rec in catalog[path]:
            if selected and rec["id"] not in selected:
                continue
            view = {}
            for k in SHOWN:
                if k in rec and rec[k] not in (None, [], ""):
                    view[k] = legend.get((k, rec[k]), rec[k]) if isinstance(rec[k], str) else rec[k]
            out.append("---\n" + yaml.safe_dump(view, allow_unicode=True, sort_keys=False, width=1000))
    if legend:
        out.insert(0, "\nRepeated values:\n" + "".join(f"{tag}: {kv[1]}\n" for kv, tag in legend.items()))
    if not (args.file or args.ids):
        for path in PROSE_PAGES:
            text = (ROOT / path).read_text(encoding="utf-8")
            text = "\n".join(l for l in text.splitlines() if not l.startswith("[Career index]"))
            out.append(f"\n##### {path} (verbatim)\n\n{text.strip()}\n")
    print("Current view: drafting fields only. Legacy metadata, source lines and evidence paths are omitted;"
          " open the raw files for those. career/story.md is a narrative for people, not evidence; use the"
          " records below for claims. For functional roles, functional_window is the user-confirmed maximum"
          " window and governs tailoring; display_dates are historical source wording, so a difference"
          " between them is not a conflict.")
    print("".join(out))


if __name__ == "__main__":
    main()
