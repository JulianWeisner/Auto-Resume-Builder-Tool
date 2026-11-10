#!/usr/bin/env python3
"""Automatic résumé check: run after rendering the PDF, before delivery.

Usage:
    python3 tools/resume_check.py RESUME.pdf [--source RESUME.html]
        [--tags tags.json --terms terms.txt] [--max-pages 2] [--json OUT.json]

Part 1, readable by screening software (applicant tracking systems first
extract a PDF's text, then search it):
  - text extracts, with no replacement or (cid:N) glyphs and all fonts embedded
  - name, email and phone from career/contact.json appear as text (empty fields are skipped)
  - Experience and Education headings appear as their own lines
  - every month-year date range uses one pattern (case and dash type ignored)
  - page count is within --max-pages
  - with --source, the PDF text keeps the source HTML's reading order
  - résumé voice: no first-person words (I, me, my, mine, myself); bullets
    take the candidate as the understood subject

Part 2, the job's terms, where evidence supports them (needs --tags and --terms).
terms.txt holds one term per line, written by the agent from the job key:
    TAG | term [/ alternative ...] [| unsupported]
  - TAG must exist in tags.json, and the first term must appear in that tag's
    quote, so every term is the employer's own wording.
  - Alternatives are other wordings that count as covering it (P&L for financials).
    An alternative must mean the same or something narrower, never broader: "Claude"
    does not cover "Claude Code". An alternative made only of words from the term
    (a dropped qualifier) is refused.
  - A hyphenated term split across two lines still counts as covered, with a note:
    text extraction drops the hyphen at a line wrap ("go-tomarket").
  - Mark a term "unsupported" only after checking the career records hold no
    evidence for it. Unsupported terms stay out of the résumé; list them in the
    private report for the cover letter or interview.

Result: PASS when part 1 has no failures and every term is covered or marked
unsupported. A missing term without the mark is a failure: the agent either
revises the wording (the records support it) or marks it unsupported.
Exit 0 on PASS, 1 on FAIL, 2 on usage or tool errors.

The check mirrors common screening-software behavior; it cannot promise how a
particular employer's system scores a résumé. Standard library plus poppler's
pdftotext, pdfinfo and pdffonts.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTACT = ROOT / "career" / "contact.json"
MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
RANGE = re.compile(
    rf"\b(?P<a>{MONTH}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})\s*(?P<dash>[-–—]|to)\s*"
    rf"(?P<b>{MONTH}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}}|present|current)\b", re.I)
REQUIRED_HEADINGS = ["Experience", "Education"]
# Résumé bullets take the candidate as the understood subject (agents/writing/plain-language.md).
FIRST_PERSON_WORDS = {"me", "my", "mine", "myself"}


def first_person(line):
    """Spans of first-person words. me/my/mine/myself in any case, but not inside
    hyphenated words ("me-too"). "I" counts only as a pronoun: at the line start,
    after punctuation or after a lowercase word, so "Phase I" and "Type I" pass."""
    spans, prev = [], None
    for m in re.finditer(r"[\w'’-]+", line):
        word = m.group(0)
        if word.lower() in FIRST_PERSON_WORDS:
            spans.append(m.span())
        elif word == "I":
            between = line[prev.end():m.start()] if prev else ""
            if prev is None or between.strip() or prev.group(0)[0].islower():
                spans.append(m.span())
        prev = m
    return spans


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit(f"resume_check: {cmd[0]} is not installed (poppler-utils)")
    except subprocess.CalledProcessError as e:
        sys.exit(f"resume_check: {cmd[0]} failed: {e.stderr.strip()}")


def squash(text):
    """Lowercase, unify dashes and quotes, collapse whitespace; for searching."""
    text = text.translate(str.maketrans({"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', " ": " "}))
    return re.sub(r"\s+", " ", text).strip().lower()


def contains(hay, needle, wrapped=False):
    """Whole-word, case-insensitive search; spaces and hyphens are interchangeable.
    wrapped=True also accepts a hyphen joint with nothing in it: when a hyphenated
    word wraps at a line end, text extraction drops the hyphen and joins the halves
    ("go-to-market" reads as "go-tomarket")."""
    pieces = re.split(r"([\s-]+)", squash(needle))
    if not any(p.strip(" -") for p in pieces):
        return False
    pat = ""
    for i, piece in enumerate(pieces):
        if i % 2 == 0:
            pat += re.escape(piece)
        else:
            pat += r"[\s-]*" if (wrapped and "-" in piece) else r"[\s-]+"
    return re.search(r"(?<![\w])" + pat + r"(?![\w])", hay) is not None


def date_kind(m):
    def one(x):
        x = x.lower()
        if re.match(MONTH + r"\s", x):
            return "Mon YYYY"
        if "/" in x:
            return "MM/YYYY"
        if x in ("present", "current"):
            return None
        return "YYYY"
    kinds = {k for k in (one(m["a"]), one(m["b"])) if k}
    return " & ".join(sorted(kinds)) or "?"


def source_lines(path):
    raw = Path(path).read_text(encoding="utf-8")
    raw = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|li|h[1-6]|div|tr|section)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return [squash(l) for l in text.splitlines() if len(squash(l).split()) >= 5]


def check_readable(pdf, text, source, max_pages):
    results = []  # (status, label, detail) with status PASS / WARN / FAIL

    def add(ok, label, detail="", warn=False):
        results.append(("PASS" if ok else ("WARN" if warn else "FAIL"), label, detail))

    flat = squash(text)
    add(len(flat) >= 200, "Text extracts from the PDF",
        f"{len(flat)} characters" if len(flat) >= 200 else "little or no text: the PDF may be an image")
    bad = len(re.findall(r"\(cid:\d+\)|�", text))
    add(bad == 0, "No unreadable characters", f"{bad} unreadable glyphs" if bad else "")
    fonts = run(["pdffonts", str(pdf)]).splitlines()[2:]
    unembedded = [l.split()[0] for l in fonts if len(l.split()) >= 5 and l.split()[-5] == "no"]
    add(not unembedded, "All fonts embedded", ", ".join(unembedded))

    contact = json.loads(CONTACT.read_text(encoding="utf-8"))
    digits = re.sub(r"\D", "", flat)
    for key in ("name", "email", "phone"):
        val = contact.get(key)
        if not val:
            continue
        found = (re.sub(r"\D", "", val) in digits) if key == "phone" else (squash(val) in flat)
        add(found, f"Contact {key} found as text", val if found else f"{val} not found in the extracted text")

    lines = [squash(l) for l in text.splitlines()]
    for h in REQUIRED_HEADINGS:
        add(h.lower() in lines, f"Heading '{h}' on its own line")
    if "skills" not in lines:
        add(False, "Heading 'Skills' on its own line", "optional; confirm the Stage 2 keyword audit kept relevant skills", warn=True)

    kinds = {}
    for m in RANGE.finditer(flat):
        kinds.setdefault(date_kind(m), []).append(m.group(0))
    if not kinds:
        add(False, "Date ranges found", "no date ranges detected")
    else:
        add(len(kinds) == 1, "Date ranges use one pattern",
            "; ".join(f"{k}: {len(v)} (e.g. {v[0]})" for k, v in kinds.items()))
    dashes = {m["dash"] for m in RANGE.finditer(text)}
    if len(dashes) > 1:
        add(False, "Date ranges use one dash", " and ".join(sorted(repr(d) for d in dashes)), warn=True)

    hits = []
    for line in text.splitlines():
        for a, b in first_person(line):
            hits.append("…" + re.sub(r"\s+", " ", line[max(a - 30, 0):b + 30]).strip() + "…")
    add(not hits, "No first-person words",
        f"{len(hits)} found, first: \"{hits[0]}\"; rewrite with the candidate as the understood subject" if hits else "")

    pages = int(re.search(r"Pages:\s+(\d+)", run(["pdfinfo", str(pdf)]))[1])
    add(pages <= max_pages, "Page count within target", f"{pages} of at most {max_pages}")

    if source:
        pos, out_of_order, missing = 0, [], []
        for line in source_lines(source):
            probe = line[:60]
            i = flat.find(probe, pos)
            if i >= 0:
                pos = i + len(probe)
            elif flat.find(probe) >= 0:
                out_of_order.append(probe)
            else:
                missing.append(probe)
        add(not out_of_order, "Reading order matches the source",
            f"{len(out_of_order)} passage(s) out of order, first: \"{out_of_order[0]}\"" if out_of_order else "")
        if missing:
            add(False, "Source passages found in the PDF text",
                f"{len(missing)} not found exactly (often line-wrap hyphenation), first: \"{missing[0]}\"", warn=True)
    return results


def check_terms(flat, tags_path, terms_path):
    tags = json.loads(Path(tags_path).read_text(encoding="utf-8"))
    rows, errors = [], []
    for n, raw in enumerate(Path(terms_path).read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.split("#", 1)[0].strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) not in (2, 3) or (len(parts) == 3 and parts[2].lower() != "unsupported"):
            errors.append(f"terms line {n}: expected 'TAG | term [/ alternative ...] [| unsupported]': {raw}")
            continue
        tag, options = parts[0], [o.strip() for o in parts[1].split("/") if o.strip()]
        unsupported = len(parts) == 3
        if tag not in tags:
            errors.append(f"terms line {n}: unknown tag {tag}")
            continue
        if not contains(squash(tags[tag]["text"]), options[0]):
            errors.append(f"terms line {n}: '{options[0]}' is not in {tag}'s quote; "
                          "use the employer's own wording first, alternatives after a slash")
            continue
        tw = set(p for p in re.split(r"[\s-]+", squash(options[0])) if p)
        broader = [o for o in options[1:] if set(p for p in re.split(r"[\s-]+", squash(o)) if p) < tw]
        if broader:
            errors.append(f"terms line {n}: '{broader[0]}' is broader than '{options[0]}', so a match "
                          "would not show the employer's term; list only alternatives that mean the same "
                          "or something narrower")
            continue
        hit = next((o for o in options if contains(flat, o)), None)
        joined = None
        if not hit:  # found only where a line wrap removed a hyphen
            joined = next((o for o in options if contains(flat, o, wrapped=True)), None)
        status = "covered" if (hit or joined) else ("unsupported" if unsupported else "missing")
        rows.append({"tag": tag, "term": options[0], "matched": hit or joined,
                     "line_wrap": bool(joined), "status": status})
    return rows, errors


def main():
    ap = argparse.ArgumentParser(description="Automatic résumé check (see module docstring).")
    ap.add_argument("pdf")
    ap.add_argument("--source", help="populated résumé HTML, to compare reading order")
    ap.add_argument("--tags", help="tags.json from jd_key.py render --save")
    ap.add_argument("--terms", help="terms file (see module docstring)")
    ap.add_argument("--max-pages", type=int, default=2)
    ap.add_argument("--json", help="also write the full result as JSON for the private report")
    a = ap.parse_args()
    if bool(a.tags) != bool(a.terms):
        ap.error("--tags and --terms go together")
    if not shutil.which("pdftotext"):
        sys.exit("resume_check: pdftotext is not installed (poppler-utils)")

    text = run(["pdftotext", a.pdf, "-"])
    flat = squash(text)
    readable = check_readable(a.pdf, text, a.source, a.max_pages)
    terms, term_errors = check_terms(flat, a.tags, a.terms) if a.tags else ([], [])
    if term_errors:
        print("\n".join(term_errors), file=sys.stderr)
        return 2

    fails = [r for r in readable if r[0] == "FAIL"]
    missing = [t for t in terms if t["status"] == "missing"]
    covered = sum(t["status"] == "covered" for t in terms)
    unsupported = sum(t["status"] == "unsupported" for t in terms)
    ok = not fails and not missing

    print("Part 1 · readable by screening software, in résumé voice")
    for status, label, detail in readable:
        print(f"  {status:<4}  {label}" + (f": {detail}" if detail else ""))
    if terms:
        print("Part 2 · job terms")
        for t in terms:
            mark = {"covered": "PASS", "unsupported": "OUT ", "missing": "FAIL"}[t["status"]]
            via = f" (as '{t['matched']}')" if t["matched"] and t["matched"] != t["term"] else ""
            if t.get("line_wrap"):
                via += ("; split by a line wrap, so screening software may read it joined without its hyphen."
                        " Reword or reflow if the term matters")
            note = {"unsupported": ": no evidence; stays out, note for the cover letter or interview",
                    "missing": ": revise the wording if the records support it; otherwise mark unsupported"}.get(t["status"], "")
            print(f"  {mark}  {t['tag']} {t['term']}{via}{note}")

    summary = "Checked: " + ("readable" if not fails else f"{len(fails)} problem(s) to fix")
    if terms:
        summary += f"; {covered} of {len(terms)} job terms covered"
        if unsupported:
            summary += f"; {unsupported} " + ("has" if unsupported == 1 else "have") + " no evidence"
        if missing:
            summary += f"; {len(missing)} still missing"
    print(("PASS  " if ok else "FAIL  ") + summary)

    if a.json:
        Path(a.json).write_text(json.dumps({
            "result": "PASS" if ok else "FAIL", "summary": summary,
            "readable": [dict(zip(("status", "check", "detail"), r)) for r in readable],
            "terms": terms}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
