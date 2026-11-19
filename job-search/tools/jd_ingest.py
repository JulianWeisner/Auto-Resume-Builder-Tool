#!/usr/bin/env python3
"""B5 job-description ingestion adapter: one source-verifiable JD artifact for
batch screening (pipeline.py) and Stage 1 (tools/jd_key.py).

Both entry routes produce the same artifact:
  HiringCafe:  jd_ingest.py ingest --source-type hiringcafe --input jd.txt \\
                   --meta meta.json [--display-blocks blocks.json] --out DIR
  Chat paste:  jd_ingest.py ingest --source-type user_paste --input - --out DIR < jd.txt
  Greenhouse:  jd_ingest.py greenhouse-text raw.json > jd.txt   (raw = saved boards-api response)
               jd_ingest.py ingest --source-type greenhouse --input jd.txt --meta meta.json --out DIR

DIR receives two files:
  jd.txt         the normalized posting: the exact source plus synthetic "\\n"
                 insertions only. This is the file jd_key.py numbers and renders.
  artifact.json  hashes, provenance, insertions, offset maps, logical blocks,
                 physical lines and (after `render`) validated selections.

Other commands:
  jd_ingest.py lines DIR               numbered lines with block ID and line role
  jd_ingest.py validate DIR            reopen and revalidate a persisted artifact
  jd_ingest.py check-map DIR MAP|-     run the guard on a jd_key map, print selections
  jd_ingest.py render DIR MAP|- [--save tags.json]
                                       guard, then tools/jd_key.py render; records the
                                       validated selections in artifact.json

Exit codes: 0 success, 1 validation or ingestion failure (machine-readable JSON
errors on stderr), 2 usage error.

Text model: the canonical source is a sequence of Unicode code points whose
UTF-8 encoding is the canonical byte string. Bytes input must be strict UTF-8
(a BOM is kept as U+FEFF, never stripped). Text input is encoded as UTF-8 and
must not contain lone surrogates. Offsets are half-open [start, end) in code
points ("source") and UTF-8 bytes ("bytes"). Normalization only inserts "\\n"
and never changes, removes or reorders a source character.

Standard library only. See job-search/README.md for the contract.
"""
import argparse
import bisect
import html
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
JD_KEY = REPO / "tools" / "jd_key.py"

SCHEMA_VERSION = "1.0"
NORMALIZER = "b5-insert-only"
NORMALIZER_VERSION = "1.0"
DEFAULT_WIDTH = 100
MIN_WIDTH = 20
# A source line this long is a flattened description (some provider connections return a whole
# posting as one paragraph). It is split into sentence blocks so each ask can be tagged on its own.
SENTENCE_SPLIT_MIN = 1500
# A provider description with fewer words than this is a stub, not a posting (for example a bare ID).
MIN_DESCRIPTION_WORDS = 25
SENTENCE_START = re.compile(r"(?<=[.!?])[\"')\]]?\s+(?=[A-Z0-9•●▪◦])|\s+(?=[•●▪◦]\s?)")
INSERT = "\n"
ARTIFACT_FILE = "artifact.json"
TEXT_FILE = "jd.txt"
SOURCE_TYPES = ("hiringcafe", "user_paste", "greenhouse")
GREENHOUSE_TEXT_VERSION = "gh-text-1"
PROVENANCE_KEYS = {
    "hiringcafe": {"provider_job_id", "url", "retrieved_at", "response_id", "response_sha256",
                   "retrieval_tool", "representation", "company", "title"},
    "user_paste": {"company", "title", "url", "supplied_at", "note"},
    "greenhouse": {"board", "provider_job_id", "url", "updated_at", "retrieved_at", "response_sha256",
                   "retrieval_tool", "representation", "company", "title"},
}
REQUIRED_PROVENANCE = {"hiringcafe": {"provider_job_id"}, "user_paste": set(),
                       "greenhouse": {"board", "provider_job_id", "response_sha256"}}
COMPLETENESS = ("complete", "truncated", "unknown")
INSERT_REASONS = ("block_boundary", "wrap")
LINE_ROLES = ("single", "start", "continuation", "end", "blank")
# Everything str.splitlines() treats as a line break; jd_key.py numbers lines the same way.
LINE_BREAKS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"
NO_BREAK = "\u00a0\u2007\u202f\ufeff"
# HiringCafe connector responses end truncated descriptions with this marker.
MARKER_RE = re.compile(r"…\(truncated — read the full posting at (?P<url>\S+?)\)\s*\Z")
SPLIT_PUNCT = ".;:,!?)]}\"'”’"
SPLIT_CONNECTORS = {"and", "or", "&", "but", "plus"}


class IngestError(Exception):
    """A failure with a stable machine-readable code."""

    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.details = code, details

    def as_dict(self):
        return {"code": self.code, "message": str(self), **self.details}


def err(code, message, **details):
    return {"code": code, "message": message, **details}


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def byte_index(text):
    """offsets[i] = UTF-8 byte offset of code point i (len(text)+1 entries)."""
    out, total = [0], 0
    for ch in text:
        o = ord(ch)
        total += 1 if o < 0x80 else 2 if o < 0x800 else 3 if o < 0x10000 else 4
        out.append(total)
    return out


def decode_source(data):
    """Return (text, utf8_bytes). Bytes must be strict UTF-8; text must be encodable."""
    if isinstance(data, (bytes, bytearray)):
        data = bytes(data)
        try:
            return data.decode("utf-8"), data
        except UnicodeDecodeError as e:
            raise IngestError("invalid_utf8", f"source is not valid UTF-8 at byte {e.start}",
                              byte_offset=e.start) from None
    if isinstance(data, str):
        try:
            return data, data.encode("utf-8")
        except UnicodeEncodeError as e:
            raise IngestError("unencodable_text", f"text has an unencodable code point at {e.start}",
                              source_offset=e.start) from None
    raise IngestError("invalid_input_type", "source must be str or bytes")


def source_lines(text):
    """[(start, content_end, end)] using str.splitlines semantics."""
    out, pos = [], 0
    for seg in text.splitlines(keepends=True):
        content = len(seg) - (2 if seg.endswith("\r\n") else 1 if seg[-1] in LINE_BREAKS else 0)
        out.append((pos, pos + content, pos + len(seg)))
        pos += len(seg)
    return out


def line_blocks(text, limit):
    """One logical block per non-blank source line, trimmed of surrounding whitespace.
    A line of SENTENCE_SPLIT_MIN code points or more is split into sentence blocks: a new block
    starts after sentence-ending punctuation followed by a capital, digit or bullet, and before an
    inline bullet character. Returns (spans, split) where split says whether any line was split."""
    spans, split = [], False
    for s, ce, _ in source_lines(text[:limit]):
        seg = text[s:ce]
        left, right = len(seg) - len(seg.lstrip()), len(seg.rstrip())
        if right <= left:
            continue
        if right - left < SENTENCE_SPLIT_MIN:
            spans.append((s + left, s + right))
            continue
        split = True
        pos = s + left
        for m in SENTENCE_START.finditer(text, s + left, s + right):
            if text[pos:m.end()].strip():
                spans.append((pos, m.end()))  # the piece keeps any closing quote; whitespace is trimmed below
                pos = m.end()
        spans.append((pos, s + right))
    spans = [(a + len(text[a:b]) - len(text[a:b].lstrip()), a + len(text[a:b].rstrip())) for a, b in spans
             if text[a:b].strip()]
    return spans, split


def align_display_blocks(text, blocks, limit):
    """Exact, in-order alignment of display blocks with text[:limit].

    Each block (surrounding whitespace ignored) must appear verbatim at the next
    non-whitespace position; only whitespace may separate blocks or follow the last.
    Returns (spans, None) or (None, failure)."""
    if not isinstance(blocks, list) or not blocks:
        return None, err("display_blocks_invalid", "display blocks must be a non-empty list of strings")
    spans, pos = [], 0
    for k, block in enumerate(blocks):
        if not isinstance(block, str) or not block.strip():
            return None, err("display_block_empty", f"display block {k} is empty or not a string",
                             block_index=k)
        core = block.strip()
        while pos < limit and text[pos].isspace():
            pos += 1
        if pos + len(core) > limit or text[pos:pos + len(core)] != core:
            return None, err("display_block_not_aligned",
                             f"display block {k} does not match the source at code point {pos}",
                             block_index=k, source_offset=pos)
        spans.append((pos, pos + len(core)))
        pos += len(core)
    if text[pos:limit].strip():
        return None, err("display_trailing_text", f"source text after the last display block at {pos}",
                         source_offset=pos)
    return spans, None


def wrap_space(ch):
    return ch.isspace() and ch not in LINE_BREAKS and ch not in NO_BREAK


def best_break(text, pos, end, width):
    """Insertion point p (pos < p < end) after a breakable space and before a non-space."""
    ok = [p for p in range(pos + 1, end) if wrap_space(text[p - 1]) and not text[p].isspace()]
    within = [p for p in ok if p - pos <= width]
    if within:
        return within[-1]
    beyond = [p for p in ok if p - pos > width]
    return beyond[0] if beyond else None  # a single overlong token is never split


def plan_insertions(text, blocks, width):
    """Sorted [(source_offset, reason)]: block boundaries first, then wrapping."""
    ins = {}
    for prev, cur in zip(blocks, blocks[1:]):
        if not any(c in LINE_BREAKS for c in text[prev[1]:cur[0]]):
            ins[cur[0]] = "block_boundary"
    cuts = sorted(ins)
    for s, ce, _ in source_lines(text):
        points = [s] + [c for c in cuts if s < c < ce] + [ce]
        for a, b in zip(points, points[1:]):
            pos = a
            while b - pos > width:
                p = best_break(text, pos, b, width)
                if p is None:
                    break
                ins[p] = "wrap"
                pos = p
    return sorted(ins.items())


def apply_insertions(text, insertions):
    parts, last = [], 0
    for off, _ in insertions:
        parts += [text[last:off], INSERT]
        last = off
    parts.append(text[last:])
    return "".join(parts)


def detect_marker(text):
    m = MARKER_RE.search(text)
    if not m:
        return None
    return {"start": m.start(), "end": m.end("url") + 1, "url": m["url"]}


def greenhouse_text(raw):
    """Deterministic description text from a saved Greenhouse boards-api job response (bytes).

    gh-text-1: unescape the API's HTML-escaped `content`; turn <br> and closing block tags into
    line breaks and <li> into "• "; drop other tags; unescape entities; replace no-break spaces with
    spaces; strip each line; keep at most one blank line in a row. The raw response hash goes into
    provenance (response_sha256) so the text can always be re-derived and checked."""
    data = json.loads(raw)
    h = html.unescape(data["content"])
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|h[1-6]|li|ul|ol|tr|table)\s*>", "\n", h)
    h = re.sub(r"(?i)<li[^>]*>", "• ", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = html.unescape(h).replace("\u00a0", " ")
    lines, blank = [], False
    for line in (x.strip() for x in h.split("\n")):
        if not line:
            if lines and not blank:
                lines.append("")
            blank = True
            continue
        lines.append(line)
        blank = False
    return "\n".join(lines).strip() + "\n"


def check_provenance(source_type, provenance):
    if source_type not in SOURCE_TYPES:
        raise IngestError("unsupported_source_type", f"source type must be one of {', '.join(SOURCE_TYPES)}",
                          source_type=source_type)
    provenance = dict(provenance or {})
    unknown = sorted(set(provenance) - PROVENANCE_KEYS[source_type])
    if unknown:
        raise IngestError("invalid_provenance", f"unsupported provenance fields for {source_type}: {unknown}",
                          fields=unknown)
    missing = sorted(REQUIRED_PROVENANCE[source_type] - set(provenance))
    if missing:
        raise IngestError("invalid_provenance", f"missing provenance fields for {source_type}: {missing}",
                          fields=missing)
    for k, v in provenance.items():
        if not isinstance(v, str) or not v.strip():
            raise IngestError("invalid_provenance", f"provenance field {k} must be a non-empty string", field=k)
    for k in ("retrieved_at", "supplied_at", "updated_at"):
        if k in provenance and not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d(\.\d+)?)?(Z|[+-]\d\d:\d\d)",
                                                provenance[k]):
            raise IngestError("invalid_provenance", f"{k} must be an ISO 8601 timestamp with a zone", field=k)
    if "response_sha256" in provenance and not re.fullmatch(r"[0-9a-f]{64}", provenance["response_sha256"]):
        raise IngestError("invalid_provenance", "response_sha256 must be 64 lowercase hex digits",
                          field="response_sha256")
    return {k: provenance[k] for k in sorted(provenance)}


def ingest(data, source_type, provenance=None, display_blocks=None, width=DEFAULT_WIDTH,
           require_display_alignment=False, completeness=None):
    """Build (artifact, normalized_text). Raises IngestError on invalid input."""
    provenance = check_provenance(source_type, provenance)
    if type(width) is not int or width < MIN_WIDTH:
        raise IngestError("invalid_width", f"width must be an integer >= {MIN_WIDTH}", width=width)
    if completeness not in (None, "complete", "truncated"):
        raise IngestError("invalid_completeness", "completeness may only be asserted as complete or truncated")
    text, raw = decode_source(data)
    if not text.strip():
        raise IngestError("empty_source", "source has no non-whitespace text")

    marker = detect_marker(text) if source_type == "hiringcafe" else None
    limit = marker["start"] if marker else len(text)
    if not text[:limit].strip():
        raise IngestError("empty_source", "source has no text before the truncation marker")
    if marker:
        if completeness == "complete":
            raise IngestError("conflicting_completeness", "source carries a provider truncation marker")
        complete = {"status": "truncated", "basis": "provider_marker", "continuation_url": marker["url"]}
    elif completeness:
        complete = {"status": completeness, "basis": "caller_asserted"}
    else:
        complete = {"status": "unknown"}
    if source_type in ("hiringcafe", "greenhouse") and complete["status"] != "truncated" \
            and len(text[:limit].split()) < MIN_DESCRIPTION_WORDS:
        # A provider stub (for example a bare job ID) is not a complete posting, whatever was asserted.
        complete = {"status": "insufficient", "basis": "too_few_words", "words": len(text[:limit].split())}

    split = False
    if display_blocks is not None:
        blocks_hash = sha256(json.dumps(display_blocks, ensure_ascii=False, separators=(",", ":")))
        spans, failure = align_display_blocks(text, display_blocks, limit)
        if failure and require_display_alignment:
            raise IngestError("display_alignment_failed", failure["message"], detail=failure)
        if failure:
            alignment = {"status": "failed", "display_blocks_sha256": blocks_hash, "failure": failure}
            spans, split = line_blocks(text, limit)
        else:
            alignment = {"status": "aligned", "display_blocks_sha256": blocks_hash, "block_count": len(spans)}
    else:
        alignment = {"status": "not_supplied"}
        spans, split = line_blocks(text, limit)
    if alignment["status"] == "aligned":
        method = "display_blocks+wrap"
    else:
        method = "line_blocks+sentences+wrap" if split else "line_blocks+wrap"

    block_spans = [(s, e, "content") for s, e in spans]
    if marker:
        block_spans.append((marker["start"], marker["end"], "provider_marker"))
    insertions = plan_insertions(text, block_spans, width)
    normalized = apply_insertions(text, insertions)
    return assemble(text, raw, normalized, insertions, block_spans, source_type, provenance, complete,
                    alignment, method, width), normalized


def assemble(text, raw, normalized, insertions, block_spans, source_type, provenance, complete,
             alignment, method, width):
    bidx = byte_index(text)
    ins_norm = [off + i for i, (off, _) in enumerate(insertions)]
    ins_set = set(ins_norm)

    def to_source(n):
        return n - bisect.bisect_left(ins_norm, n)

    blocks = []
    last_content = max((i for i, b in enumerate(block_spans) if b[2] == "content"), default=None)
    for i, (s, e, kind) in enumerate(block_spans):
        tail = kind == "content" and i == last_content and complete["status"] == "truncated"
        blocks.append({"id": f"U{i + 1:03d}", "kind": kind, "source": [s, e], "bytes": [bidx[s], bidx[e]],
                       "sha256": sha256(raw[bidx[s]:bidx[e]]), "lines": None,
                       "selectable": kind == "content" and not tail, "truncated_tail": tail})
    starts = [b["source"][0] for b in blocks]

    lines = []
    for n, (ns, nce, ne) in enumerate(source_lines(normalized), 1):
        ss, se = to_source(ns), to_source(nce)
        term = "none" if ne == nce else ("synthetic" if nce in ins_set else "source")
        k = bisect.bisect_right(starts, se - 1) - 1 if se > ss else -1
        owner = None
        if k >= 0 and blocks[k]["source"][0] < se and ss < blocks[k]["source"][1]:
            owner = blocks[k]
            if k + 1 < len(blocks) and blocks[k + 1]["source"][0] < se:
                raise IngestError("internal_error", f"line {n} intersects two logical blocks")
        elif text[ss:se].strip():
            raise IngestError("internal_error", f"line {n} has text outside every logical block")
        lines.append({"n": n, "normalized": [ns, nce], "source": [ss, se], "bytes": [bidx[ss], bidx[se]],
                      "terminator": term, "block": owner["id"] if owner else None, "role": "blank"})
        if owner:
            owner["lines"] = [owner["lines"][0] if owner["lines"] else n, n]
    for b in blocks:
        a, z = b["lines"]
        for ln in lines[a - 1:z]:
            if ln["block"] == b["id"]:
                ln["role"] = "single" if a == z else "start" if ln["n"] == a else "end" if ln["n"] == z \
                    else "continuation"

    canonical_sha = sha256(raw)
    normalized_raw = normalized.encode("utf-8")
    return {
        "artifact_type": "jd_ingest_artifact",
        "schema_version": SCHEMA_VERSION,
        "artifact_id": f"jd-{canonical_sha[:16]}-{sha256(normalized_raw)[:8]}",
        "source": {"type": source_type, "provenance": provenance,
                   "provenance_basis": "user_supplied" if source_type == "user_paste" else "caller_supplied",
                   **({"text_derivation": GREENHOUSE_TEXT_VERSION} if source_type == "greenhouse" else {}),
                   "completeness": complete},
        "canonical": {"sha256": canonical_sha, "utf8_bytes": len(raw), "code_points": len(text)},
        "normalization": {"normalizer": NORMALIZER, "version": NORMALIZER_VERSION, "method": method,
                          "width": width, "width_unit": "code_points", "insertion_text": INSERT,
                          "display_alignment": alignment},
        "normalized": {"file": TEXT_FILE, "sha256": sha256(normalized_raw), "utf8_bytes": len(normalized_raw),
                       "code_points": len(normalized), "physical_lines": len(lines)},
        "insertions": [{"source": off, "bytes": bidx[off], "normalized": off + i, "reason": reason}
                       for i, (off, reason) in enumerate(insertions)],
        "blocks": blocks,
        "lines": lines,
        "selections": None,
        "validation": {"status": "valid", "checks": ["canonical_hash", "insert_only_reconstruction",
                                                     "offset_maps", "block_membership"]},
    }


# --- persistence -----------------------------------------------------------------------------------

def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def write_artifact(out_dir, artifact, normalized):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / TEXT_FILE).write_bytes(normalized.encode("utf-8"))
    (out / ARTIFACT_FILE).write_text(dump_json(artifact), encoding="utf-8")


def load_artifact(art_dir):
    d = Path(art_dir)
    try:
        artifact = json.loads((d / ARTIFACT_FILE).read_text(encoding="utf-8"))
        raw = (d / TEXT_FILE).read_bytes()
    except (OSError, ValueError) as e:
        raise IngestError("artifact_unreadable", f"cannot read artifact in {d}: {e}") from None
    try:
        normalized = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise IngestError("normalized_invalid_utf8", f"{TEXT_FILE} is not valid UTF-8 at byte {e.start}",
                          byte_offset=e.start) from None
    return artifact, normalized


def reconstruct(artifact, normalized):
    """Remove the recorded insertions; return (canonical_text, errors)."""
    errors, ins = [], artifact.get("insertions")
    if not isinstance(ins, list):
        return None, [err("insertion_invalid", "insertions must be a list")]
    remove, prev = [], -1
    for i, x in enumerate(ins):
        try:
            n, s = x["normalized"], x["source"]
            ok = type(n) is int and type(s) is int and n == s + i and n > prev and x["reason"] in INSERT_REASONS
        except (KeyError, TypeError):
            ok = False
        if not ok or not (0 <= n < len(normalized)) or normalized[n] != INSERT:
            errors.append(err("insertion_invalid", f"insertion {i} is not a recorded synthetic newline",
                              insertion_index=i))
            return None, errors
        remove.append(n)
        prev = n
    keep = set(remove)
    return "".join(ch for k, ch in enumerate(normalized) if k not in keep), errors


def validate_artifact(artifact, normalized, check_selections=True):
    """Revalidate a persisted artifact. Returns a list of error dicts (empty when valid)."""
    if not isinstance(artifact, dict) or artifact.get("artifact_type") != "jd_ingest_artifact":
        return [err("artifact_invalid", "not a JD ingestion artifact")]
    if artifact.get("schema_version") != SCHEMA_VERSION:
        return [err("unsupported_schema_version", f"schema_version must be {SCHEMA_VERSION}")]
    norm = artifact.get("normalization") or {}
    if norm.get("normalizer") != NORMALIZER or norm.get("version") != NORMALIZER_VERSION:
        return [err("unsupported_normalizer", "unknown normalizer or version")]
    meta = artifact.get("normalized") or {}
    nraw = normalized.encode("utf-8")
    if sha256(nraw) != meta.get("sha256") or len(nraw) != meta.get("utf8_bytes"):
        return [err("normalized_hash_mismatch", f"{TEXT_FILE} does not match the recorded normalized hash")]
    canonical, errors = reconstruct(artifact, normalized)
    if errors:
        return errors
    craw = canonical.encode("utf-8")
    can = artifact.get("canonical") or {}
    if sha256(craw) != can.get("sha256") or len(craw) != can.get("utf8_bytes") \
            or len(canonical) != can.get("code_points"):
        return [err("reconstruction_mismatch", "reconstructed source does not match the canonical hash")]

    # Rebuild every derived field from the canonical bytes and recorded parameters.
    src = artifact.get("source") or {}
    complete = src.get("completeness") or {}
    asserted = complete.get("status") if complete.get("basis") == "caller_asserted" else None
    alignment = norm.get("display_alignment") or {}
    display = None
    if alignment.get("status") == "aligned":
        try:
            display = [canonical[b["source"][0]:b["source"][1]] for b in artifact["blocks"]
                       if b["kind"] == "content"]
        except (KeyError, TypeError, IndexError):
            return [err("block_invalid", "blocks are malformed")]
    try:
        rebuilt, rebuilt_text = ingest(craw, src.get("type"), src.get("provenance"), display,
                                       norm.get("width"), completeness=asserted)
    except IngestError as e:
        return [err("artifact_mismatch", f"artifact cannot be rebuilt: {e}", cause=e.as_dict())]
    if alignment.get("status") == "aligned":
        rebuilt["normalization"]["display_alignment"]["display_blocks_sha256"] = \
            alignment.get("display_blocks_sha256")
    elif alignment.get("status") == "failed":
        # A failed alignment fell back to line blocks; its record is informational.
        rebuilt["normalization"]["display_alignment"] = alignment
    if rebuilt_text != normalized:
        return [err("artifact_mismatch", "normalized text differs from a deterministic rebuild")]
    for key in rebuilt:
        if key == "selections":
            continue
        if rebuilt[key] != artifact.get(key):
            return [err("artifact_mismatch", f"field {key} differs from a deterministic rebuild", field=key)]
    extra = sorted(set(artifact) - set(rebuilt))
    if extra:
        return [err("artifact_mismatch", f"unexpected fields: {extra}", fields=extra)]

    sel = artifact.get("selections")
    if sel is not None and check_selections:
        if not isinstance(sel, dict) or not isinstance(sel.get("map"), list):
            return [err("selections_invalid", "selections must record the map that produced them")]
        if sha256("\n".join(sel["map"])) != sel.get("map_sha256"):
            return [err("selections_invalid", "map_sha256 does not match the recorded map")]
        items, errors = check_map(artifact, normalized, sel["map"], canonical=canonical)
        if errors:
            return errors
        if items != sel.get("items"):
            return [err("selections_invalid", "recorded selections differ from a rebuild of the recorded map")]
    return []


def validate_dir(art_dir):
    try:
        artifact, normalized = load_artifact(art_dir)
    except IngestError as e:
        return None, None, [e.as_dict()]
    return artifact, normalized, validate_artifact(artifact, normalized)


# --- selection guard -------------------------------------------------------------------------------

def jd_key_module():
    if str(JD_KEY.parent) not in sys.path:
        sys.path.insert(0, str(JD_KEY.parent))
    import jd_key
    return jd_key


def check_map(artifact, normalized, map_lines, canonical=None):
    """Validate a jd_key map against the artifact before rendering.

    Returns (selections, errors). Rules:
    - A tag without a quoted span must cover whole logical blocks; covering only some
      of a block's physical lines is a wrap fragment.
    - A tag with a quoted span is an intentional semantic selection. It may lie inside
      one block (a split) or cover whole blocks, never part of one block and part of another.
    - A split block's other text must be covered by other tags; leftover words are an error.
    - Splits may not meet at a synthetic wrap point unless punctuation or a connector
      marks the boundary.
    - skip must cover whole blocks. Provider markers and truncated tails are not selectable.
    """
    jk = jd_key_module()
    if canonical is None:
        canonical, errors = reconstruct(artifact, normalized)
        if errors:
            return None, errors
    craw = canonical.encode("utf-8")
    bidx = byte_index(canonical)
    lines = normalized.splitlines()
    rec_lines = artifact["lines"]
    blocks = {b["id"]: b for b in artifact["blocks"]}
    order = [b["id"] for b in artifact["blocks"]]
    ins_norm = [x["normalized"] for x in artifact["insertions"]]
    wraps = {x["source"] for x in artifact["insertions"] if x["reason"] == "wrap"}
    line_start = [ln["normalized"][0] for ln in rec_lines]
    errors, items, skipped = [], [], set()

    def to_source(n):
        return n - bisect.bisect_left(ins_norm, n)

    def blocks_in(a, b):
        seen = []
        for ln in rec_lines[a - 1:b]:
            if ln["block"] and ln["block"] not in seen:
                seen.append(ln["block"])
        return seen

    def core_start(bid):
        """Block start after any leading bullet marker, which jd_key never quotes."""
        bs, be = blocks[bid]["source"]
        bl = jk.BULLET.match(canonical[bs:be])
        return bs + bl.end() if bl and bl.end() < be - bs else bs

    def touching(s, e):
        return [bid for bid in order if blocks[bid]["source"][0] < e and s < blocks[bid]["source"][1]]

    for mn, raw in enumerate(map_lines, 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        m = jk.MAP_LINE.match(raw)
        if not m:
            errors.append(err("map_parse_error", f"map line {mn}: cannot parse", map_line=mn))
            continue
        tag, a = m["tag"], int(m["a"])
        b = int(m["b"] or a)
        if not 1 <= a <= b <= len(lines):
            errors.append(err("line_range_invalid", f"map line {mn}: L{a}-L{b} outside 1-{len(lines)}",
                              map_line=mn, tag=tag))
            continue
        in_range = blocks_in(a, b)
        partial = [bid for bid in in_range if not (a <= blocks[bid]["lines"][0] and blocks[bid]["lines"][1] <= b)]
        if tag == "skip":
            for bid in partial:
                errors.append(err("skip_partial_block", f"map line {mn}: skip L{a}-L{b} covers part of {bid} "
                                  f"(L{blocks[bid]['lines'][0]}-L{blocks[bid]['lines'][1]})",
                                  map_line=mn, block=bid))
            skipped.update(in_range)
            continue
        rm = jk.REST.match((m["rest"] or "").strip())
        if not rm:
            errors.append(err("map_parse_error", f"map line {mn} ({tag}): cannot parse span or shorthand",
                              map_line=mn, tag=tag))
            continue
        parts, offsets, pos = [], [], 0
        for n in range(a, b + 1):
            offsets.append((n, pos))
            parts.append(lines[n - 1])
            pos += len(lines[n - 1]) + 1
        block_text = " ".join(parts)
        if rm["span"]:
            sm = jk.SPAN.match(rm["span"])
            if sm:
                span, problem = jk.find_span(block_text, sm["s"], sm["e"])
            else:
                phrase = rm["span"].strip()[1:-1]
                span, problem = jk.find_span(block_text, phrase, phrase)
            if problem:
                errors.append(err("span_not_found", f"map line {mn} ({tag}): {problem}", map_line=mn, tag=tag))
                continue
            i, j = span
            mode = "span"
        else:
            i, j, mode = 0, len(block_text), "whole_blocks"

        def norm_at(k):
            """Normalized offset of block_text[k], a real character (never a joining space)."""
            for n, off in reversed(offsets):
                if k >= off:
                    return line_start[n - 1] + (k - off)
            raise IngestError("internal_error", "span offset before block start")

        rendered = re.sub(r"\s+", " ", jk.strip_bullet(block_text[i:j])).strip()
        if mode == "whole_blocks":
            if not in_range:
                errors.append(err("selection_empty", f"map line {mn} ({tag}): no text in L{a}-L{b}",
                                  map_line=mn, tag=tag))
                continue
            for bid in partial:
                blk = blocks[bid]
                errors.append(err("wrap_fragment",
                                  f"map line {mn} ({tag}): L{a}-L{b} takes part of {bid}, which runs "
                                  f"L{blk['lines'][0]}-L{blk['lines'][1]}; cover the whole block or quote "
                                  "an intentional span", map_line=mn, tag=tag, block=bid,
                                  block_lines=blk["lines"]))
            if partial:
                continue
            s, e = blocks[in_range[0]]["source"][0], blocks[in_range[-1]]["source"][1]
            bullet = jk.BULLET.match(canonical[s:e])
            if bullet and bullet.end() < e - s:
                s += bullet.end()
            touched = in_range
        else:
            s, e = to_source(norm_at(i)), to_source(norm_at(j - 1) + 1)
            if e <= s:
                errors.append(err("offset_invalid", f"map line {mn} ({tag}): empty source span",
                                  map_line=mn, tag=tag))
                continue
            touched = touching(s, e)
            whole = [bid for bid in touched if s <= core_start(bid) and blocks[bid]["source"][1] <= e]
            if len(touched) > 1 and len(whole) != len(touched):
                errors.append(err("block_boundary_crossed",
                                  f"map line {mn} ({tag}): span takes part of one block and part of "
                                  f"another ({', '.join(touched)})", map_line=mn, tag=tag, blocks=touched))
                continue
        for bid in touched:
            blk = blocks[bid]
            if blk["kind"] == "provider_marker":
                errors.append(err("selection_in_marker", f"map line {mn} ({tag}): {bid} is a provider marker",
                                  map_line=mn, tag=tag, block=bid))
            elif blk["truncated_tail"]:
                errors.append(err("selection_in_truncated_tail",
                                  f"map line {mn} ({tag}): {bid} is cut off by provider truncation",
                                  map_line=mn, tag=tag, block=bid))
        split_of = None
        if len(touched) == 1 and not (s <= core_start(touched[0]) and blocks[touched[0]]["source"][1] <= e):
            split_of = touched[0]
        quote = canonical[s:e]
        items.append({"tag": tag, "map_line": raw, "lines": [a, b], "mode": mode, "blocks": touched,
                      "split_of": split_of, "source": [s, e], "bytes": [bidx[s], bidx[e]],
                      "quote": quote, "quote_sha256": sha256(craw[bidx[s]:bidx[e]]),
                      "rendered_text": rendered})

    seen = {}
    for it in items:
        if it["tag"] in seen:
            errors.append(err("duplicate_tag", f"duplicate tag {it['tag']}", tag=it["tag"]))
        seen[it["tag"]] = it
    ordered = sorted(items, key=lambda x: x["source"])
    for x, y in zip(ordered, ordered[1:]):
        if y["source"][0] < x["source"][1]:
            errors.append(err("selection_overlap", f"{x['tag']} and {y['tag']} share source text",
                              tags=[x["tag"], y["tag"]]))
    for it in items:
        hit = skipped & set(it["blocks"])
        if hit:
            errors.append(err("skip_overlaps_selection", f"{it['tag']} selects text in skipped {sorted(hit)}",
                              tag=it["tag"], blocks=sorted(hit)))
    for bid in sorted({it["split_of"] for it in items if it["split_of"]}):
        bs, be = blocks[bid]["source"]
        pieces = sorted((it for it in items if bid in it["blocks"]), key=lambda x: x["source"])
        mask = list(canonical[bs:be])
        for it in pieces:
            for k in range(max(it["source"][0], bs), min(it["source"][1], be)):
                mask[k - bs] = " "
        leftover = jk.strip_bullet("".join(mask))
        if re.search(r"[^\W_]", leftover):
            excerpt = re.sub(r"\s+", " ", leftover).strip()[:80]
            errors.append(err("split_remainder_uncovered", f"{bid} is split but this text has no tag: {excerpt}",
                              block=bid, tags=[it["tag"] for it in pieces]))
        for x, y in zip(pieces, pieces[1:]):
            gap_lo, gap_hi = x["source"][1], y["source"][0]
            if any(gap_lo <= w <= gap_hi for w in wraps) and not canonical[gap_lo:gap_hi].strip():
                before = canonical[:gap_lo].rstrip()[-1:]
                after = re.match(r"[\w&]+", canonical[gap_hi:])
                if before not in SPLIT_PUNCT and not (after and after.group(0).lower() in SPLIT_CONNECTORS):
                    errors.append(err("split_at_wrap_boundary",
                                      f"{x['tag']} and {y['tag']} divide {bid} exactly at a synthetic wrap "
                                      "with no punctuation or connector; quote complete phrases",
                                      block=bid, tags=[x["tag"], y["tag"]]))
    return items, errors


def selections_record(map_lines, items):
    kept = [ln.strip() for ln in map_lines if ln.strip()]
    renderer = JD_KEY.read_bytes() if JD_KEY.exists() else b""
    return {"map": kept, "map_sha256": sha256("\n".join(kept)), "items": items,
            "renderer": {"path": "tools/jd_key.py", "sha256": sha256(renderer)}}


def render(art_dir, map_text, save=None, record=True):
    """Guard, then tools/jd_key.py render. Returns (exit_code, key_markdown, errors, stderr)."""
    artifact, normalized, errors = validate_dir(art_dir)
    if errors:
        return 1, "", errors, ""
    map_lines = map_text.splitlines()
    items, errors = check_map(artifact, normalized, map_lines)
    if errors:
        return 1, "", errors, ""
    with tempfile.TemporaryDirectory() as tmp:
        tags_path = Path(tmp) / "tags.json"
        proc = subprocess.run([sys.executable, str(JD_KEY), "render", str(Path(art_dir) / TEXT_FILE), "-",
                               "--save", str(tags_path)], input=map_text, capture_output=True, text=True,
                              encoding="utf-8")
        if proc.returncode != 0:
            return 1, "", [err("renderer_failed", "tools/jd_key.py render rejected the map",
                               exit_code=proc.returncode)], proc.stderr
        tags = json.loads(tags_path.read_text(encoding="utf-8"))
    by_tag = {it["tag"]: it for it in items}
    problems = []
    if set(tags) != set(by_tag):
        problems.append(err("renderer_output_mismatch", "renderer tags differ from guarded selections",
                            renderer=sorted(tags), guard=sorted(by_tag)))
    for tag, t in tags.items():
        it = by_tag.get(tag)
        if it and (t.get("text") != it["rendered_text"] or t.get("lines") != it["lines"]):
            problems.append(err("renderer_output_mismatch", f"{tag}: renderer text or lines differ from guard",
                                tag=tag))
    if problems:
        return 1, "", problems, proc.stderr
    if save:
        Path(save).write_text(json.dumps(tags, ensure_ascii=False, indent=1), encoding="utf-8")
    if record:
        artifact["selections"] = selections_record(map_lines, items)
        (Path(art_dir) / ARTIFACT_FILE).write_text(dump_json(artifact), encoding="utf-8")
    return 0, proc.stdout, [], proc.stderr


def verify_quote(artifact, canonical, ref, quote):
    """Check a search-run requirement's source reference. Returns a list of error strings."""
    sel = artifact.get("selections") or {}
    items = {it["tag"]: it for it in sel.get("items", [])}
    out = []
    tag = ref.get("tag")
    s, e = ref.get("source", [None, None]) if isinstance(ref.get("source"), list) else (None, None)
    if tag not in items:
        return [f"source tag {tag!r} is not a validated selection in {artifact.get('artifact_id')}"]
    it = items[tag]
    if not (type(s) is int and type(e) is int and it["source"][0] <= s < e <= it["source"][1]):
        return [f"source offsets {ref.get('source')} are not inside selection {tag} {it['source']}"]
    exact = canonical[s:e]
    if ref.get("quote_sha256") != sha256(exact):
        out.append(f"quote_sha256 does not match source[{s}:{e}]")
    if quote not in (exact, re.sub(r"\s+", " ", exact).strip()):
        out.append("quote is not the exact source slice (or its whitespace-collapsed form)")
    return out


# --- command line ----------------------------------------------------------------------------------

def read_input(path):
    return sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()


def fail(errors, stderr=""):
    if stderr:
        sys.stderr.write(stderr)
    sys.stderr.write(json.dumps({"status": "invalid", "errors": errors}, ensure_ascii=False, indent=1) + "\n")
    return 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="jd_ingest.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest")
    pi.add_argument("--source-type", required=True, choices=SOURCE_TYPES)
    pi.add_argument("--input", required=True, help="JD file, or - for stdin (raw bytes)")
    pi.add_argument("--meta", help="JSON object of provenance fields")
    pi.add_argument("--display-blocks", help="JSON list of HiringCafe display block strings")
    pi.add_argument("--require-display-alignment", action="store_true")
    pi.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    pi.add_argument("--completeness", choices=("complete", "truncated"))
    pi.add_argument("--out", required=True)
    for name in ("lines", "validate"):
        sub.add_parser(name).add_argument("dir")
    sub.add_parser("greenhouse-text").add_argument("raw")
    pc = sub.add_parser("check-map")
    pc.add_argument("dir")
    pc.add_argument("map")
    pr = sub.add_parser("render")
    pr.add_argument("dir")
    pr.add_argument("map")
    pr.add_argument("--save")
    args = p.parse_args(argv)

    if args.cmd == "greenhouse-text":
        try:
            sys.stdout.write(greenhouse_text(read_input(args.raw)))
        except (OSError, ValueError, KeyError) as e:
            return fail([err("input_unreadable", f"not a Greenhouse job response: {e}")])
        return 0
    if args.cmd == "ingest":
        try:
            meta = json.loads(Path(args.meta).read_text(encoding="utf-8")) if args.meta else None
            blocks = json.loads(Path(args.display_blocks).read_text(encoding="utf-8")) \
                if args.display_blocks else None
            if meta is not None and not isinstance(meta, dict):
                raise IngestError("invalid_provenance", "--meta must hold a JSON object")
            artifact, normalized = ingest(read_input(args.input), args.source_type, meta, blocks, args.width,
                                          args.require_display_alignment, args.completeness)
        except IngestError as e:
            return fail([e.as_dict()])
        except (OSError, ValueError) as e:
            return fail([err("input_unreadable", str(e))])
        write_artifact(args.out, artifact, normalized)
        print(json.dumps({"status": "valid", "artifact_id": artifact["artifact_id"], "dir": args.out,
                          "canonical_sha256": artifact["canonical"]["sha256"],
                          "normalized_sha256": artifact["normalized"]["sha256"],
                          "method": artifact["normalization"]["method"],
                          "completeness": artifact["source"]["completeness"]["status"],
                          "blocks": len(artifact["blocks"]), "physical_lines": len(artifact["lines"])},
                         ensure_ascii=False, indent=1))
        return 0

    artifact, normalized, errors = validate_dir(args.dir)
    if errors:
        return fail(errors)
    if args.cmd == "validate":
        print(json.dumps({"status": "valid", "artifact_id": artifact["artifact_id"],
                          "selections": len((artifact.get("selections") or {}).get("items", []))}, indent=1))
        return 0
    if args.cmd == "lines":
        for ln, text in zip(artifact["lines"], normalized.splitlines()):
            if ln["block"]:
                print(f"L{ln['n']:02d}  {ln['block']} {ln['role']:<12} {text.rstrip()}")
        return 0
    map_text = sys.stdin.read() if args.map == "-" else Path(args.map).read_text(encoding="utf-8")
    if args.cmd == "check-map":
        items, errors = check_map(artifact, normalized, map_text.splitlines())
        if errors:
            return fail(errors)
        print(json.dumps({"status": "valid", "items": items}, ensure_ascii=False, indent=1))
        return 0
    code, key, errors, stderr = render(args.dir, map_text, args.save)
    if code:
        return fail(errors, stderr)
    sys.stdout.write(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
