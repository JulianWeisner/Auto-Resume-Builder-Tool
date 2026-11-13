#!/usr/bin/env python3
"""Job-description key builder: the agent labels, the script copies and expands.

1. Number (script):   jd_key.py number JD.txt
   Prints the posting with stable line numbers. No interpretation.

2. Map and render (agent writes the map; one command):
       jd_key.py render JD.txt - --save tags.json > key.md <<'MAP'
       Role-1  L12  "You're not satisfied" ... "lasting business impact." = want to understand behaviors and incentives that create impact
       Do-1    L22  = Identify and solve problems through data, customer insights and experimentation
       Want-3  L25-L26
       skip    L56-L65  salary, benefits and EEO boilerplate
       MAP

   Map line: TAG LINES [SPAN] [= SHORTHAND]
   - TAG: Prefix-N (About, Role, Do, Want, Nice, ...) or "skip".
   - LINES: L12 or L12-L14 (inclusive).
   - SPAN (optional): "start words" ... "end words" (also … or ..), matched word
     for word inside those lines; or one quoted phrase, "Founder background is a
     plus.", for text without double quotes inside it. Omit it to take the whole
     line(s).
   - SHORTHAND (optional): the agent's trimmed version of the quote. It may only
     remove words from the full quote, never add or change them; "and", "or" and
     commas may be added. Keep the action verb and any qualifier that sets the bar.
   - Level words (requirement tags only, not About or Cond): a shorthand must keep every level-setting term in its quote
     (extensive, complex, high-impact, proven, exceptional, excellent, strong,
     independently, staff, senior, years, "without relying", "not just", ...)
     and every number.
   - For skip, everything after the lines is the reason.
   Prints the verbatim key and a Not-mapped list; --save writes the tags, full
   quotes and shorthands for step 3. Exits 1 on a span not found verbatim,
   uncovered text, a duplicate tag or a shorthand that adds or changes words; on
   failure the key and the errors go to stderr and nothing goes to stdout.

3. Assemble (script):  jd_key.py assemble tags.json [--scores scores.txt] head.md key.md body.md > stage1.md
   scores.txt (private) gives every tag a 0-4 score, one "TAG SCORE" per line, except
   condition tags, which take pass, fail or unknown ("Cond-1 pass"); add
   "trait" after the score for asks that name a personal trait ("Want-2 2 trait").
   assemble prints the fit baseline: the weighted average / 4 x 100, with Cond tags
   left out and About and trait tags at half weight, then the conditions' pass/fail list.
   assemble checks every tag is scored and prints a private summary to stderr,
   including requirements scored 1 or below; scores never enter the output.
   Concatenates the files and expands placeholders the agent wrote:
       {Do-1'}   the agent's shorthand         *Identify and solve problems through ...* (Do-1)
   Full quotes appear only in the key; {Do-1} outside the key is an error.
   Adjacent placeholders form one group:  {Role-1'} {Want-1'}  ->
       "..."; "..." (Role-1, Want-1)
   A shorthand that is an unbroken excerpt of the quote is shown in quotation
   marks; a trimmed one is shown in italics, so nothing is presented as an exact
   quote unless it is one. Escaped \\{Do-1\\} is left alone. Exits 1 on unknown
   tags or a missing shorthand. Reports tags never referenced, which belong in
   Not mapped with a reason.

Standard library only.
"""
import json
import re
import sys
from collections import OrderedDict

BULLET = re.compile(r"^\s*(?:[*\-•●▪–]|\d+[.)])\s+")
TAG_RE = r"[A-Za-z][\w&]*-\d+[a-z]?"
MAP_LINE = re.compile(
    rf"^(?P<tag>{TAG_RE}|skip)\s+"
    r"L(?P<a>\d+)(?:\s*-\s*L?(?P<b>\d+))?"
    r"(?:\s+(?P<rest>.*))?$"
)
REST = re.compile(
    r'^(?P<span>["“].+?["”]\s*(?:\.\.\.?|…)\s*["“].+?["”]|["“][^"“”]+["”])?'
    r"\s*(?:=\s*(?P<short>.+))?$"
)
SPAN = re.compile(r'^["“](?P<s>.+?)["”]\s*(?:\.\.\.?|…)\s*["“](?P<e>.+?)["”]\s*$')
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                        "–": "-", "—": "-", " ": " "})
PLACEHOLDER = rf"(?<!\\)\{{{TAG_RE}['’]?\}}"
GROUP = re.compile(rf"{PLACEHOLDER}(?:[ \t]*{PLACEHOLDER})*")
ONE = re.compile(rf"\{{({TAG_RE})(['’]?)\}}")
CONNECTORS = {"and", "or"}
# Words and phrases that set the level of a requirement. A shorthand must keep
# every one that appears in its full quote, plus every number.
LEVEL_TERMS = ["extensive", "complex", "high-impact", "proven", "exceptional", "excellent",
               "strong", "independently", "too-many-to-count", "staff", "senior", "expert",
               "advanced", "years", "without relying", "not just"]
MIN_UNCOVERED = 25  # characters of leftover text that count as a gap


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def norm_with_index(text):
    """Normalized text (quotes/dashes unified, whitespace collapsed, lowercase)
    plus a map from each normalized char back to its original index."""
    out, idx, prev_space = [], [], False
    for i, ch in enumerate(text.translate(QUOTES)):
        if ch.isspace():
            if prev_space or not out:
                continue
            out.append(" "); idx.append(i); prev_space = True
        else:
            out.append(ch.lower()); idx.append(i); prev_space = False
    return "".join(out), idx


def norm(text):
    return norm_with_index(text)[0].strip()


def words(text):
    return re.findall(r"[\w'&$%+/.-]+", norm(text).replace(".", " ").replace("/", " "))


def strip_bullet(line):
    return BULLET.sub("", line, count=1).strip()


def trim_only_problem(short, full):
    """None if every word of short appears in full, in order (connectors may be added)."""
    fw, pos, prev = words(full), 0, None
    for w in words(short):
        if w in CONNECTORS:  # connectors may be added anywhere; never consume quote words
            continue
        try:
            pos = fw.index(w, pos) + 1
        except ValueError:
            near = f'"{prev} {w}"' if prev else f'"{w}"'
            return (f"not a trimmed version of the quote near {near}: "
                    "use only the quote's own words, in order (you may add and, or, commas). If a trim does not read smoothly, keep a longer unbroken phrase from the quote instead of adding words")
        prev = w
    return None


def level_problem(short, full):
    """None if the shorthand keeps every level-setting term and number in the full quote."""
    f, sh = " " + " ".join(words(full)) + " ", " " + " ".join(words(short)) + " "
    # "staff" sets a level ("staff engineer") but not inside a title ("Chief of Staff").
    f, sh = f.replace(" of staff ", " of_staff "), sh.replace(" of staff ", " of_staff ")
    dropped = [t for t in LEVEL_TERMS if f" {t} " in f and f" {t} " not in sh]
    dropped += [n for n in re.findall(r"\d[\d,.+%]*", norm(full)) if n not in norm(short)]
    if dropped:
        return "drops level-setting words " + ", ".join(f'"{d}"' for d in dropped) + "; keep them"
    return None


def is_excerpt(short, full):
    return norm(short).strip(" .,;:") in norm(full)


def cmd_number(jd_path):
    for n, line in enumerate(load(jd_path), 1):
        if line.strip():
            print(f"L{n:02d}  {line.rstrip()}")


def find_span(block, start, end):
    """Return (i, j) in block so block[i:j] runs from start phrase to end phrase."""
    nb, idx = norm_with_index(block)
    s, e = norm(start), norm(end)
    i = nb.find(s)
    if i < 0:
        return None, f'start phrase not found: "{start}"'
    j = nb.find(e, i)
    if j < 0:
        return None, f'end phrase not found after start: "{end}"'
    j_end = j + len(e) - 1
    return (idx[i], idx[j_end] + 1), None


def cmd_render(jd_path, map_path, save=None):
    lines = load(jd_path)
    errors, entries, skips = [], [], []
    covered = {n: [] for n in range(1, len(lines) + 1)}  # list of (i, j) char spans
    tagged = {}  # line -> [(i, j, tag)] for overlap checks between tags

    map_lines = sys.stdin.read().splitlines() if map_path == "-" else load(map_path)
    for mn, raw in enumerate(map_lines, 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        m = MAP_LINE.match(raw)
        if not m:
            errors.append(f"map line {mn}: cannot parse: {raw}")
            continue
        a = int(m["a"]); b = int(m["b"] or a)
        if not (1 <= a <= b <= len(lines)):
            errors.append(f"map line {mn}: line range L{a}-L{b} outside posting (1-{len(lines)})")
            continue
        rest = (m["rest"] or "").strip()
        if m["tag"] == "skip":
            skips.append((a, b, rest or "(no reason given)"))
            for n in range(a, b + 1):
                covered[n].append((0, len(lines[n - 1])))
            continue
        rm = REST.match(rest)
        if not rm:
            errors.append(f'map line {mn}: expected [\"start\" ... \"end\"] [= shorthand]: {rest}')
            continue
        # Build the block: join lines with single spaces, tracking line offsets.
        parts, offsets, pos = [], [], 0
        for n in range(a, b + 1):
            offsets.append((n, pos)); parts.append(lines[n - 1]); pos += len(lines[n - 1]) + 1
        block = " ".join(parts)
        if rm["span"]:
            sm = SPAN.match(rm["span"])
            if sm:
                span, err = find_span(block, sm["s"], sm["e"])
            else:  # one quoted phrase: the span is exactly that text
                phrase = rm["span"].strip()[1:-1]
                span, err = find_span(block, phrase, phrase)
            if err:
                errors.append(f"map line {mn} ({m['tag']}): {err}")
                continue
            i, j = span
        else:
            i, j = 0, len(block)
        for n, off in offsets:  # mark coverage per original line
            ln = len(lines[n - 1])
            lo, hi = max(i - off, 0), min(j - off, ln)
            if lo < hi:
                for plo, phi, ptag in tagged.get(n, []):  # two tags must not share text
                    if lo < phi and plo < hi:
                        shared = re.sub(r"\s+", " ", lines[n - 1][max(lo, plo):min(hi, phi)]).strip()
                        errors.append(f'map line {mn} ({m["tag"]}) overlaps {ptag} on L{n:02d} ("{shared[:60]}"); '
                                      "split the spans so each piece of text has one tag")
                tagged.setdefault(n, []).append((lo, hi, m["tag"]))
                covered[n].append((lo, hi))
        text = re.sub(r"\s+", " ", strip_bullet(block[i:j])).strip()
        short = (rm["short"] or "").strip() or None
        if short:
            context = m["tag"].split("-")[0] in ("About", "Cond")  # level words bind requirements only
            problem = trim_only_problem(short, text) or (None if context else level_problem(short, text))
            if problem:
                errors.append(f"map line {mn} ({m['tag']}) shorthand: {problem}")
        entries.append((m["tag"], a, b, text, short))

    seen = {}
    for tag, a, *_ in entries:
        if tag in seen:
            errors.append(f"duplicate tag {tag} (L{seen[tag]} and L{a})")
        seen[tag] = a

    # Coverage: leftover text on each line, ignoring bullets and punctuation.
    gaps, headings = [], []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        mask = [False] * len(line)
        for lo, hi in covered[n]:
            for k in range(lo, min(hi, len(line))):
                mask[k] = True
        leftover = "".join(" " if mask[k] else ch for k, ch in enumerate(line))
        leftover = strip_bullet(leftover)
        if len(re.sub(r"[\W_]+", "", leftover)) == 0:
            continue
        if not covered[n] and len(line.split()) <= 6 and not line.rstrip().endswith((".", "!", "?")):
            headings.append((n, line.strip()))  # heading-like lines: listed, not errors
            continue
        if len(leftover.strip()) >= MIN_UNCOVERED:
            gaps.append((n, re.sub(r"\s+", " ", leftover).strip()))

    groups = OrderedDict()
    for e in entries:
        groups.setdefault(e[0].rsplit("-", 1)[0], []).append(e)
    out = ["## Job-description key (verbatim)\n"]
    for items in groups.values():
        for tag, a, b, text, short in items:
            out.append(f'- **\\{{{tag}\\}}** "{text}"')
    out.append("\n## Not mapped\n")
    for a, b, reason in skips:
        rng = f"L{a:02d}" if a == b else f"L{a:02d}-L{b:02d}"
        out.append(f"- {rng}: {reason}")
    for n, h in headings:
        out.append(f"- L{n:02d}: section heading ({h})")
    if gaps:
        out.append("\n## Uncovered text (fix the map)\n")
        out.extend(f"- L{n:02d}: {g}" for n, g in gaps)
    if errors:
        out.append("\n## Map errors (fix the map)\n")
        out.extend(f"- {e}" for e in errors)
    if errors or gaps:
        # On failure nothing goes to stdout, so a redirected key.md is never a partial key.
        print("\n".join(out), file=sys.stderr)
        print(f"\nrender failed: {len(errors)} map error(s), {len(gaps)} uncovered line(s); "
              "nothing written to stdout. Fix the map and rerun.", file=sys.stderr)
        return 1
    print("\n".join(out))
    if save:
        data = OrderedDict((tag, {"text": text, "short": short, "lines": [a, b]})
                           for tag, a, b, text, short in entries)
        with open(save, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return 0


def is_condition(tag):
    """Condition tags (Cond-N) are a pass/fail filter, never part of the fit score."""
    return tag.rsplit("-", 1)[0] == "Cond"


def load_scores(path, tags, errors, traits=None):
    scores = {}
    for n, raw in enumerate(load(path), 1):
        raw = raw.split("#", 1)[0].strip()
        if not raw:
            continue
        m = re.match(rf"^({TAG_RE})\s+([0-4]|pass|fail|unknown)(\s+trait)?$", raw)
        if not m:
            errors.append(f"scores line {n}: expected 'TAG SCORE [trait]' with SCORE 0-4, "
                          f"or 'Cond-N pass|fail|unknown' for a condition: {raw}")
        elif m[1] not in tags:
            errors.append(f"scores line {n}: unknown tag {m[1]}")
        elif is_condition(m[1]) != (not m[2].isdigit()):
            errors.append(f"scores line {n}: {m[1]}: conditions take pass, fail or unknown; "
                          f"every other tag takes a 0-4 score")
        else:
            scores[m[1]] = m[2] if is_condition(m[1]) else int(m[2])
            if m[3] and traits is not None:
                traits.add(m[1])
    missing = [t for t in tags if t not in scores]
    if missing:
        errors.append("unscored tags (score every tag in the key): " + ", ".join(missing))
    return scores


def fit_baseline(scores, traits):
    """Weighted average of 0-4 scores as a percentage: Cond tags left out (gates);
    About tags and trait-marked tags at half weight; all others full weight."""
    total = weight = 0.0
    for tag, sc in scores.items():
        prefix = tag.rsplit("-", 1)[0]
        if is_condition(tag):
            continue
        w = 0.5 if (prefix == "About" or tag in traits) else 1.0
        total += w * sc; weight += w
    return (total / weight / 4 * 100) if weight else None


def score_summary(scores, traits=frozenset()):
    conditions = {t: v for t, v in scores.items() if is_condition(t)}
    scores = {t: v for t, v in scores.items() if not is_condition(t)}
    groups = OrderedDict()
    for tag, sc in scores.items():
        groups.setdefault(tag.rsplit("-", 1)[0], []).append(sc)
    lines = ["Per-requirement scores (private; not part of the report):"]
    for g, v in groups.items():
        dist = " ".join(f"{k}:{v.count(k)}" for k in (4, 3, 2, 1, 0) if v.count(k))
        lines.append(f"  {g:<6} n={len(v):<2} mean={sum(v) / len(v):.1f}  {dist}")
    low = [t for t, sc in scores.items() if sc <= 1]
    if low:
        lines.append("Scored 1 or below (in 1.1, weigh these for the verdict's main gaps; in 1.2-1.4, show each "
                     "in its own table row or under Not covered, not hidden in a merged row): " + ", ".join(low))
    base = fit_baseline(scores, traits)
    if base is not None:
        lines.append(f"Fit baseline: {base:.1f}% (Cond left out; About and trait tags at half weight: "
                     + (", ".join(sorted(traits)) or "no traits marked") + "). Final fit = baseline "
                     "adjusted by at most 5 points, with a one-sentence reason.")
    if conditions:
        lines.append("Conditions (pass/fail filter, not in the fit): "
                     + ", ".join(f"{t} {v}" for t, v in conditions.items())
                     + ". Show each on the card; any fail means Deprioritize, naming it; "
                     "ask about an unknown when it could change the decision.")
    return "\n".join(lines)


def cmd_assemble(tags_path, paths, scores_path=None):
    with open(tags_path, encoding="utf-8") as f:
        tags = json.load(f)
    errors, used = [], set()
    traits = set()
    scores = load_scores(scores_path, tags, errors, traits) if scores_path else None

    def render_group(m):
        parts, names = [], []
        for tag, mark in ONE.findall(m.group(0)):
            if tag not in tags:
                errors.append(f"unknown tag {{{tag}{mark}}}")
                return m.group(0)
            used.add(tag); names.append(tag)
            full, short = tags[tag]["text"], tags[tag]["short"]
            if mark:
                if not short:
                    errors.append(f"{{{tag}'}} used but the map gives no shorthand for {tag}")
                    return m.group(0)
                parts.append(f'"{short}"' if is_excerpt(short, full) else f"*{short}*")
            else:
                errors.append(f"{{{tag}}} expands to the full quote; outside the key use {{{tag}'}} "
                              f"(give {tag} a shorthand in the map if it has none)")
                return m.group(0)
        return "; ".join(parts) + f" ({', '.join(names)})"

    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            out.append(GROUP.sub(render_group, f.read()))
    sys.stdout.write("\n".join(t.rstrip("\n") + "\n" for t in out))
    if scores is not None:
        print(score_summary(scores, traits), file=sys.stderr)
    unused = [t for t in tags if t not in used]
    if unused:
        print("Not referenced in the table or storyboard (list each under Not mapped with a reason): "
              + ", ".join(unused), file=sys.stderr)
    if errors:
        print("\n".join(sorted(set(errors))), file=sys.stderr)
        return 1
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "number":
        cmd_number(argv[2]); return 0
    if len(argv) >= 4 and argv[1] == "render":
        save = argv[argv.index("--save") + 1] if "--save" in argv else None
        return cmd_render(argv[2], argv[3], save)
    if len(argv) >= 4 and argv[1] == "assemble":
        args, scores = argv[2:], None
        if "--scores" in args:
            i = args.index("--scores"); scores = args[i + 1]; del args[i:i + 2]
        return cmd_assemble(args[0], args[1:], scores)
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
