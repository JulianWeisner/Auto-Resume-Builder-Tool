#!/usr/bin/env python3
"""Print AGENTS.md plus the modules its routing table lists for one task.

For AI chat tools that cannot open files in a folder (a chat window where you
upload files, a custom GPT): paste or upload the output instead.

    python3 tools/agent_bundle.py                 # list tasks
    python3 tools/agent_bundle.py resume > bundle.md

Task names come from the first column of the Routing table in AGENTS.md: the
first word, lowercased (for example "Résumé formatting" -> "résumé", also
accepted without accents as "resume"). The routing table is the single source;
this script only reads it. Standard library only.
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
        key = plain(re.split(r"[\s:,(]", label, maxsplit=1)[0])
        rows[key] = (label, r)
    return rows


def main(argv):
    core = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    rows = routing_rows(core)
    if len(argv) != 2 or plain(argv[1]) not in rows:
        print(__doc__)
        print("Tasks:")
        for key, (label, _) in rows.items():
            print(f"  {key:<12} {label}")
        return 2
    label, row = rows[plain(argv[1])]
    paths = []
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", row):
        if target not in paths:
            paths.append(target)
    out = [f"<!-- Bundle for task '{label}': AGENTS.md + {', '.join(paths)} -->", core]
    for rel in paths:
        text = (ROOT / rel).read_text(encoding="utf-8")
        fence = "```json\n" + text + "\n```" if rel.endswith(".json") else text
        out.append(f"\n\n<!-- ===== {rel} ===== -->\n\n{fence}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
