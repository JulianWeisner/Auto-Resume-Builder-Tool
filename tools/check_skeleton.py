#!/usr/bin/env python3
"""Skeleton guard for the upstream tool repository. Read-only; exits 1 on any failure.

The public tool repository must contain the tool and an EMPTY career skeleton,
never anyone's career data. This check enforces that:

  1. Data areas (career/ except career/_templates/, source-material/,
     applications/, Curriculum-Vitae.md) contain only the skeleton files listed
     in SKELETON_FILES. Any other file there fails: records, CVs, PDFs, archives.
  2. Skeleton pages contain no fenced YAML records.
  3. career/contact.json has every contact value empty.
  4. No text file anywhere contains an email address, phone number or LinkedIn
     profile URL (example.com, example.org and noreply addresses are allowed).
  5. Optional private denylist: one term per line (names, employers, record ID
     prefixes). Read from --denylist PATH, the ARB_DENYLIST environment variable,
     or .private-denylist.txt at the repository root (git-ignored). Matching is
     case-insensitive. Keep the denylist out of Git: it would itself be personal data.

Your own private copy fails this check by design once you fill it in. It runs
automatically only on the upstream repository (see .github/workflows/).

Usage: python3 tools/check_skeleton.py [--denylist PATH]
Standard library only.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_AREAS = ["career", "source-material", "applications"]
DATA_FILES = ["Curriculum-Vitae.md"]
TEMPLATES = "career/_templates"

# The complete, empty skeleton. Adding a skeleton page means adding it here, on purpose.
SKELETON_FILES = {
    "Curriculum-Vitae.md",
    "career/README.md",
    "career/story.md",
    "career/preferences.md",
    "career/vocabulary.md",
    "career/contact.json",
    "career/experience/records.md",
    "career/education/records.md",
    "career/additional/records.md",
    "source-material/README.md",
    "source-material/journal.md",
    "source-material/cv/README.md",
    "source-material/documents/README.md",
    "applications/README.md",
}

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yml", ".yaml", ".py", ".html", ".css", ".js", ".toml", ".cfg", ""}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
ALLOWED_EMAIL = re.compile(r"(@example\.(com|org)$|^noreply@)", re.I)
PHONE = re.compile(r"(?<![\w.])(\+?\d{1,2}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w])")
LINKEDIN = re.compile(r"linkedin\.com/in/[A-Za-z0-9_-]+", re.I)

errors = []


def rel(p):
    return p.relative_to(ROOT).as_posix()


def walk():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def in_data_area(path):
    if path in DATA_FILES:
        return True
    if path.startswith(TEMPLATES + "/"):
        return False
    return any(path.startswith(area + "/") for area in DATA_AREAS)


def load_denylist(argv):
    path = None
    if "--denylist" in argv:
        i = argv.index("--denylist")
        if i + 1 >= len(argv):
            sys.exit("--denylist needs a path")
        path = Path(argv[i + 1])
    elif os.environ.get("ARB_DENYLIST"):
        path = Path(os.environ["ARB_DENYLIST"])
    elif (ROOT / ".private-denylist.txt").exists():
        path = ROOT / ".private-denylist.txt"
    if path is None:
        return []
    terms = [t.strip() for t in path.read_text(encoding="utf-8").splitlines()]
    return [t for t in terms if t and not t.startswith("#")]


def main(argv):
    denylist = load_denylist(argv)
    seen = set()

    for p in walk():
        path = rel(p)
        if path == ".private-denylist.txt":
            continue
        if in_data_area(path):
            seen.add(path)
            if path not in SKELETON_FILES:
                errors.append(f"{path}: not part of the empty skeleton. Career data never belongs in the tool repository.")
                continue
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{path}: unreadable as text")
            continue

        if in_data_area(path) and path.endswith(".md") and re.search(r"^```ya?ml\b", text, re.M):
            errors.append(f"{path}: contains a YAML record block; skeleton pages hold guidance only.")

        for n, line in enumerate(text.splitlines(), 1):
            for m in EMAIL.finditer(line):
                if not ALLOWED_EMAIL.search(m.group(0)):
                    errors.append(f"{path}:{n}: email address")
            if PHONE.search(line):
                errors.append(f"{path}:{n}: phone number")
            if LINKEDIN.search(line):
                errors.append(f"{path}:{n}: LinkedIn profile URL")
            low = line.lower()
            for term in denylist:
                if term.lower() in low:
                    errors.append(f"{path}:{n}: denylisted term")
                    break

    for path in sorted(SKELETON_FILES - seen):
        errors.append(f"{path}: skeleton page is missing")

    contact = ROOT / "career/contact.json"
    if contact.exists():
        data = json.loads(contact.read_text(encoding="utf-8"))
        for key, value in data.items():
            if key != "provenance" and value not in ("", None):
                errors.append(f"career/contact.json: '{key}' must be empty in the tool repository")

    if errors:
        print(f"Skeleton check FAILED ({len(errors)}):")
        for e in errors:
            print("  - " + e)
        return 1
    note = f"; denylist of {len(denylist)} terms applied" if denylist else ""
    print(f"Skeleton check passed: {len(SKELETON_FILES)} skeleton pages, no career data{note}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
