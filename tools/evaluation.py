"""Shared evaluation policy for search and Stage 1; no workflow-specific routing.

New evaluations use POLICY, including identical credit, weights, rounding, bounded documented adjustment
and the same Promising / Stretch / Deprioritize label rule.

shared-2: credit = score / 4. Ported from the upstream project, where it was set on
2026-11-17 and earlier policies were removed.
"""
import math
import os
import re
from pathlib import Path

POLICY = "shared-2"
CREDIT = {"shared-2": lambda score: score / 4}
POLICIES = set(CREDIT)
KINDS = {"want", "do", "nice", "role", "about", "trait", "condition"}
PROMISING, STRETCH, DEPRIORITIZE = "Promising", "Stretch", "Deprioritize"
LABELS = (PROMISING, STRETCH, DEPRIORITIZE)
BANDS = {PROMISING: 75, STRETCH: 60}  # final fit at or above the number; below Stretch is Deprioritize


def assess(requirements, adjustment=0, reason=None, policy=POLICY):
    if policy not in CREDIT:
        raise ValueError("unknown evaluation policy")
    credit = CREDIT[policy]
    if reason is not None and not isinstance(reason, str):
        raise ValueError("adjustment reason must be text or null")
    if type(adjustment) not in (int, float) or not math.isfinite(adjustment) or abs(adjustment) > 5:
        raise ValueError("adjustment must be a finite number between -5 and +5 percentage points")
    if adjustment and not (isinstance(reason, str) and reason.strip()):
        raise ValueError("nonzero adjustment needs a documented reason")
    seen, points, total = set(), 0.0, 0.0
    for ask in requirements:
        kind = ask.get("kind")
        if kind not in KINDS:
            raise ValueError("unknown requirement kind")
        if kind == "condition":
            continue
        cid, score = ask.get("competency_id"), ask.get("score")
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise ValueError("score each unique competency exactly once")
        seen.add(cid)
        if type(score) is not int or not 0 <= score <= 4:
            raise ValueError("every scored ask needs an integer score from 0 to 4")
        weight = 0.5 if kind in {"about", "trait", "nice"} else 1.0
        points += credit(score) * weight
        total += weight
    baseline = points / total * 100 if total else None
    if baseline is None and adjustment:
        raise ValueError("cannot adjust an evaluation with no scored asks")
    return {"evaluation_policy": policy, "baseline_fit": round(baseline, 4) if baseline is not None else None,
            "adjustment": adjustment, "adjustment_reason": reason or None,
            "functional_fit": round(max(0, min(100, baseline + adjustment))) if baseline is not None else None}


PRIORITY = {"want": 0, "role": 1, "do": 2, "nice": 3, "trait": 4, "about": 5}


def tag_kind(tag, traits=frozenset()):
    """A source tag's kind comes from its prefix (Want-3 -> want); a trait mark overrides it."""
    if tag in traits:
        return "trait"
    kind = str(tag).rsplit("-", 1)[0].lower()
    if kind == "cond":
        return "condition"
    if kind not in PRIORITY:
        raise ValueError("unknown source tag kind")
    return kind


def kind_for_tags(tags, traits=frozenset()):
    """The kind a group of merged source tags is weighted as, in both workflows:
    the highest-priority kind among its tags (a required ask outranks a nice-to-have)."""
    kinds = [tag_kind(t, traits) for t in tags]
    if not kinds or "condition" in kinds:
        raise ValueError("conditions are gates and never take a scored kind")
    return min(kinds, key=PRIORITY.get)


def check_kind(kind, tags):
    """Search sets kind by hand; it must match what Stage 1 derives from the same source tags.
    Only `trait` may override the prefix, because Stage 1 marks traits separately from tags."""
    if kind == "trait":
        return None
    expected = kind_for_tags(tags)
    if kind != expected:
        return f"kind {kind} does not match source tags {tags} (expected {expected} or trait)"
    return None


def from_tags(scores, traits=frozenset(), groups=None):
    """Stage 1 tags -> unique asks. Groups optionally map competency IDs to tag lists.
    Every scored non-condition tag must belong to exactly one group when supplied.
    Repeated quotes retain tags in the key while one competency enters the math.
    """
    scored = {t: v for t, v in scores.items() if not t.startswith("Cond-")}
    groups = groups if groups is not None else {t: [t] for t in scored}
    if not isinstance(groups, dict):
        raise ValueError("groups must map competency IDs to lists of source tags")
    used, asks = set(), []
    for cid, tags in groups.items():
        if not isinstance(tags, list) or not tags:
            raise ValueError("each competency group needs source tags")
        values = set()
        for tag in tags:
            if tag not in scored or tag in used:
                raise ValueError("unknown, condition or multiply grouped source tag")
            used.add(tag); values.add(scored[tag])
        if len(values) != 1:
            raise ValueError("merged restatements must have the same evidence score")
        asks.append({"competency_id": cid, "kind": kind_for_tags(tags, traits),
                     "score": next(iter(values)), "source_tags": tags})
    if used != set(scored):
        raise ValueError("every measured source tag must be grouped exactly once")
    return asks


def is_mandatory(ask):
    """A required ask: one of its source tags is a Want tag (an explicit qualification), in both workflows.
    Search drafts without source tags fall back to their own mandatory flag."""
    tags = ask.get("source_tags")
    if tags:
        return any(str(t).rsplit("-", 1)[0] == "Want" for t in tags)
    return ask.get("mandatory") is True


def gap_counts(requirements):
    """(critical, unresolved, met, total) over required competencies, by score alone so both workflows agree.
    critical: scored 0-1 (or contradicted by dated records); unresolved: scored 2; met: scored 3-4."""
    critical = unresolved = met = total = 0
    for ask in requirements:
        if ask.get("kind") == "condition" or not is_mandatory(ask):
            continue
        total += 1
        score = ask.get("score")
        if ask.get("qualification_status") == "unmet" or (type(score) is int and score <= 1):
            critical += 1
        elif score == 2:
            unresolved += 1
        else:
            met += 1
    return critical, unresolved, met, total


def label(fit, critical=0, unresolved=0, condition_failed=False, knocked_out=False, stale=False):
    """Promising / Stretch / Deprioritize from the final fit, then the gates.
    - A failed condition, or an early knockout (2+ critical gaps or a gap on a defining ask), is Deprioritize.
    - The fit band sets the starting label: 75+ Promising, 60-74 Stretch, below 60 Deprioritize.
    - A critical gap, an unresolved (score 2) requirement or a stale posting moves Promising to Stretch.
    - A stale posting also moves Stretch to Deprioritize. Nothing moves a label more than one level.
    Returns None when there is no fit and no gate decided it (for example an evaluation error)."""
    if condition_failed or knocked_out:
        return DEPRIORITIZE
    if fit is None:
        return None
    base = PROMISING if fit >= BANDS[PROMISING] else STRETCH if fit >= BANDS[STRETCH] else DEPRIORITIZE
    if base == PROMISING and (critical or unresolved or stale):
        return STRETCH
    if base == STRETCH and stale:
        return DEPRIORITIZE
    return base


def decide(requirements, fit, conditions=(), knocked_out=False, stale=False):
    """Label plus the counts shown beside it. conditions: pass/fail/unknown values."""
    critical, unresolved, met, total = gap_counts(requirements)
    return {"label": label(fit, critical, unresolved, "fail" in conditions, knocked_out, stale),
            "requirements_met": {"met": met, "total": total}, "critical_gaps": critical,
            "stale_posting": bool(stale)}


def career_repo():
    """The folder whose career/ holds the records: this repository, or ARB_CAREER_REPO when set
    (for example examples/sample-person, to try the tools or run the tests on the made-up sample person)."""
    return Path(os.environ.get("ARB_CAREER_REPO") or Path(__file__).resolve().parents[1]).resolve()


def career_ids(repo=None):
    """Every record ID in the career collections, career/_templates excluded (standard library only)."""
    root = Path(repo) if repo else career_repo()
    ids = set()
    for p in (root / "career").rglob("*.md"):
        if "_templates" in p.parts:
            continue
        ids |= set(re.findall(r'^id:\s*"?([^"\s]+)"?', p.read_text(encoding="utf-8"), re.M))
    return ids
