#!/usr/bin/env python3
"""Print the current, drafting-relevant fields of every career record.

Read-only. The quickest way for an agent to read the whole career record before
evaluating a job or drafting. Raw record files remain authoritative for
verification and editing.

Collections are found automatically: every Markdown file under career/ that
holds fenced YAML records, except career/_templates/. Add a collection folder
and it appears here with no change to this script.

Every YAML key must be classified below as SHOWN or OMITTED. An unclassified
key stops the script with an error, so new qualification fields cannot vanish
from this view silently.

Requires Python 3 and PyYAML (pip install pyyaml).

Usage: python3 tools/current_view.py [--file PATH ...] [--ids ID ...]
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CAREER = ROOT / "career"
# Prose pages with user-confirmed content that is not stored as YAML records.
# Printed verbatim after the records in a full (unfiltered) view.
PROSE_PAGES = ["career/preferences.md"]
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
YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.S)


def collections():
    """Every career Markdown file with at least one YAML record, newest-edited order not implied."""
    found = []
    for p in sorted(CAREER.rglob("*.md")):
        if "_templates" in p.relative_to(CAREER).parts:
            continue
        if YAML_BLOCK.search(p.read_text(encoding="utf-8")):
            found.append(p.relative_to(ROOT).as_posix())
    return found


def records(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    for block in YAML_BLOCK.findall(text):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "id" in data:
            yield data


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", nargs="*", help="limit to these collection files")
    ap.add_argument("--ids", nargs="*", help="limit to these record IDs")
    args = ap.parse_args()
    all_files = collections()
    files = args.file or all_files
    if not all_files:
        print("The career record has no records yet. Ask your agent to help fill it (see START.md).")
        return
    unknown = set()
    out = []
    # Long text values repeated across many records are printed once in a legend.
    counts = {}
    for path in all_files:
        for rec in records(path):
            for k, v in rec.items():
                if isinstance(v, str) and len(v) > 40:
                    counts[(k, v)] = counts.get((k, v), 0) + 1
    legend = {kv: f"[{kv[0]} default {i + 1}]" for i, kv in
              enumerate(sorted(kv for kv, n in counts.items() if n >= 5))}
    for path in files:
        out.append(f"\n##### {path}\n")
        for rec in records(path):
            unknown |= set(rec) - set(SHOWN) - OMITTED
            if args.ids and rec["id"] not in args.ids:
                continue
            view = {}
            for k in SHOWN:
                if k in rec and rec[k] not in (None, [], ""):
                    view[k] = legend.get((k, rec[k]), rec[k]) if isinstance(rec[k], str) else rec[k]
            out.append("---\n" + yaml.safe_dump(view, allow_unicode=True, sort_keys=False, width=1000))
    if legend:
        out.insert(0, "\nRepeated values:\n" + "".join(f"{tag}: {kv[1]}\n" for kv, tag in legend.items()))
    if unknown:
        sys.exit("current_view.py: unclassified field(s) " + ", ".join(sorted(unknown))
                 + ". Add each to SHOWN or OMITTED in tools/current_view.py, and document it in"
                 " schema/experience-schema.md, before relying on this view.")
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
