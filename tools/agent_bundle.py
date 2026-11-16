#!/usr/bin/env python3
"""Print AGENTS.md plus the modules its routing table lists for one task.

For AI chat tools that cannot open files in a folder (a chat window where you
upload files, a custom GPT): paste or upload the output instead.

    python3 tools/agent_bundle.py                 # list tasks
    python3 tools/agent_bundle.py stage-1 > bundle.md
    python3 tools/agent_bundle.py d stage-1 > bundle.md   # a report for one stage

Task names come from the first column of the Routing table in AGENTS.md: the
text before the first colon, lowercased with spaces as hyphens (for example
"Stage 1: ..." -> "stage-1", "H: handoff" -> "h"). The routing table is the
single source; this script only reads it. For d (reports), name the stage the
report is about; the default is stage-2. Standard library only.
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def plain(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def routing_rows(core):
    if "## Routing" not in core:
        sys.exit("AGENTS.md has no Routing section.")
    section = core.split("## Routing", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for r in section.splitlines():
        if not r.startswith("| ") or r.startswith("| Task") or "---" in r:
            continue
        label = r.split("|")[1].strip()
        head = re.sub(r"\s*\(.*?\)", "", label.split(":", 1)[0])
        key = re.sub(r"[^\w.]+", "-", plain(head).strip()).strip("-")
        rows[key] = (label, r)
    return rows


def main(argv):
    core = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    rows = routing_rows(core)
    args = [plain(a) for a in argv[1:]]
    stages = [k for k in rows if k.startswith("stage-")]
    ok = len(args) == 1 and args[0] in rows
    ok = ok or (len(args) == 2 and args[0] == "d" and "d" in rows and args[1] in stages)
    if not ok:
        print(__doc__)
        print("Tasks:")
        for key, (label, _) in rows.items():
            print(f"  {key:<12} {label}")
        return 2
    picked = [rows[args[0]]]
    if args[0] == "d":
        stage = args[1] if len(args) == 2 else "stage-2"
        if stage in rows:
            picked.append(rows[stage])
    label = " + ".join(lbl for lbl, _ in picked)
    paths = list(dict.fromkeys(re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", "\n".join(r for _, r in picked))))
    out = [f"<!-- Bundle for task '{label}': AGENTS.md + {', '.join(paths)} -->", core]
    for rel in paths:
        text = (ROOT / rel).read_text(encoding="utf-8")
        fence = "```json\n" + text + "\n```" if rel.endswith(".json") else text
        out.append(f"\n\n<!-- ===== {rel} ===== -->\n\n{fence}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
