# Shared job evaluation standard

Part of the [agent guide](../AGENTS.md). **Load when:** judging how well a job fits the user's record: career informed search, the Stage 1 fit check, a full evaluation, a comparison of several postings, or the private evaluation done before a résumé build. This is the one scoring and interpretation policy. [Search](job-search.md) and [Stage 1](stage-1-evaluate.md) hold the workflow steps, not alternative standards, so a job gets the same fit and label wherever it is evaluated.

## Source and measurable asks

Keep the original posting unchanged. Where you can run Python, ingest it with `job-search/tools/jd_ingest.py` into a source artifact with stable lines and blocks, then build and render a complete selection and skip map through it (it guards `tools/jd_key.py`; [Stage 1, step 1](stage-1-evaluate.md#preparation-always)). Every substantive passage is tagged or skipped with a reason. Select every responsibility, qualification and nice-to-have. Tag stated conditions separately, including a location in the posting's header. Select measurable context and role asks no other tag covers; skip what cannot be measured, with an explicit reason. The key must account for all substantive text, not just the convenient asks. An explicit skip is not permission to discard a difficult measurable ask.

Split independent AND asks; keep genuine OR alternatives together. Keep every quote unchanged. Merge restatements into one competency while keeping all their tags: a repeated responsibility or qualification is measured once, by its most specific wording. `groups.json` maps a competency ID to its source tags, and every measured non-condition tag appears in exactly one group. Merged restatements get the same evidence rating. Conditions are never merged with scored asks. Classify each ask by [Classifying asks](#classifying-asks).

In search, each requirement carries `source_tags`, a verified primary source quote and reference, and its evidence; `coverage.map_sha256` identifies the guarded map. A full evaluation accounts for every selected tag. A job stopped at the qualification screen may record remaining tags under `coverage.deferred` with a reason; it has no full fit. Condition conflicts and incomplete postings can stop a job before full interpretation (L1). Coverage checks prove accounting and exact sources, not that the interpretation is right.

## Evidence rubric

Use the current accounts, role windows, limitations and clarifications in the career record. Search the whole career for relevant evidence (`python3 tools/current_view.py --search` with the posting's words and likely alternatives); do not rely on title keywords.

| Score | Meaning |
|---:|---|
| 4 🟢 | Direct or transferable work of the kind asked, with a stated result in the records |
| 3 🟢 | Direct or transferable work, without a stated result for this kind of ask |
| 2 🟡 | Related work that shows the capability indirectly |
| 1 🟠 | Thin, adjacent or unconfirmed evidence |
| 0 🔴 | No maintained evidence after targeted retrieval |

Every score above 0 cites at least one career record ID; with nothing to cite, the score is 0. The user's confirmed recollections count as evidence once they are in a record; independent corroboration is not required. Keep uncertainty and attribution of metrics in what you write. Work in another industry does not automatically cap a demonstrated capability at 3. Do not infer a capability the records only touch from adjacent work (for example shipped AI features from AI planning documents, or managing managers from leading a team). A gap in the record is a reason to ask, not proof that the user lacks the capability.

## Classifying asks

Classify every selected ask by these rules before rating it. The tag prefix records the classification, and the prefix sets the weight.

| Classification | Tag | Weight |
|---|---|---|
| Explicit qualification | Want | 1 |
| Role-description sentence stating an ask no Do, Want or Nice covers | Role | 1 |
| Responsibility | Do | 1 |
| Preferred or nice-to-have | Nice | 0.5 |
| Company, industry or customer context | About | 0.5 |
| Personal disposition (`trait` mark on any tag) | any + `trait` | 0.5 |
| Location, schedule, travel, work authorization | Cond | gate only |

- **Mandatory sections:** items under headings that list what the candidate must have (Requirements, Required, Qualifications, Minimum or Basic qualifications, What you'll need or bring, Must have, What we're looking for, Competencies, Ideal background, Qualities that will help you thrive, You will be successful if you have) are Want. Items under Preferred, Nice to have, Bonus, Plus or "is a plus" wording are Nice. An item's own wording wins over its heading: "6+ years preferred" under "Required" is Nice. A sub-heading (for example "Technical Skills") takes its parent section's status.
- **Responsibilities** ("What you'll do", "Responsibilities") are Do. They never become qualifications because the requirements section is short. Only explicit qualifications are mandatory. Keep inferred concerns separate; they cannot create a knockout or a gap.
- **Traits:** mark an ask as a trait only when it describes a personal disposition with no object of work (curious, high ownership, low ego). Anything that names experience, a track record or a skill is not a trait, even when it uses adjectives. A trait under a mandatory heading stays mandatory and keeps half weight.
- **Restatements:** merge every restatement into the most specific qualification and keep all its tags in the group; the group is weighted as its highest-ranking tag (Want, then Role, Do, Nice, trait, About). A responsibility that only restates a qualification does not become a second competency. Merge all wording about managing the same kind of team (manage, lead, coach, hire or mentor) into one competency per job.
- **Domain:** company or industry context is one About ask. A domain the posting requires as a qualification is a Want at full weight. When a domain gap already has a competency, fold further responsibilities in that same domain into it instead of scoring each.
- **OR alternatives** stay one competency; any alternative can satisfy it.
- **Motivation and mission fit** ("a passion for…", "excited about our mission", "you care about…"): skip with the reason `motivation ask; not scored`. Records cannot prove enthusiasm, and a 0 would only distort the fit. Carry it to the cover letter or answers instead. A trait with a behaviour attached ("comfort taking ownership in an evolving area") is still scored.
- **Split paragraphs that hold several asks** into separate tags with quoted spans, so each tag carries one ask and only its own level words. A whole-paragraph tag hides independent asks and makes short labels fail the level-word check.

## Conditions

Conditions are gates, never part of the fit. Mark each condition tag `pass` (it matches), `fail` (it conflicts) or `unknown` (the posting or the preferences leave it open). Search and Stage 1 use one copy of the rules, the `conditions` block of `career/search-criteria.yaml` (the machine-readable copy of [career goals and preferences](../career/preferences.md)), and one checker, `tools/conditions.py`: search L1 calls it, and Stage 1 runs `python3 tools/conditions.py --location "…" --workplace hybrid [--travel N]` and copies its result into the Cond tag.

- **Location:** an onsite or hybrid role passes when any listed location is within `radius_miles` of the user's `center`, measured in a straight line to the place's nearest ZIP-code centroid. A US place beyond it fails. A place the list cannot find, or a region only partly inside, is unknown: ask. Names the user listed for their whole area (`metro_aliases`) pass.
- **Remote:** a US-based or unlocated remote role passes. A remote role based outside the US is unknown (ask), because the recorded work authorization covers US roles.
- **Workplace:** a type the user does not accept (`acceptable_workplaces`) fails.
- **Travel:** up to `travel_percent_max` passes; more is unknown (ask), never a failure.
- **Work authorization** and any other stated condition: judged from the posting text against the preferences. A condition that conflicts fails in both workflows: Stage 1 labels the job Deprioritize; search excludes it, citing the source-verified quote.
- **Pay** is a search-only filter: L1 fails a posting whose posted range tops out below `minimum_annual_usd`, and a posting without pay passes. Stage 1 shows the posted pay but does not gate on it.

The checker knows US places only. Outside the US, or when the search criteria have no center yet, judge from the preferences and ask when unsure; a preference the check needs that is not recorded becomes a question, and the answer belongs in a handoff.

## One calculation, one adjustment policy and one label

`tools/evaluation.py` computes the fit and the label, policy `shared-2`:

- Per-competency credit is `score / 4`: 0 earns nothing, 1 a quarter, 2 half, 3 three quarters, 4 full credit.
- Context (About), traits and nice-to-haves have weight 0.5. Other scored competencies have weight 1. Conditions never enter the fit.
- Baseline = weighted mean of credit × 100, stored to four decimal places.
- An optional adjustment is between -5 and +5 percentage points and needs a concrete reason. Correct a misread ask or a changed evidence rating first; an adjustment cannot substitute for that correction.
- Final fit is `round(clamp(baseline + adjustment, 0, 100))`. Use the engine's result; do not round or choose a displayed percentage yourself.
- Record the policy, baseline, adjustment, reason and final fit separately, and show baseline and adjustment beside the final fit. An adjustment cannot override a condition failure, resolve an unmet qualification or rescue a knockout.

**Requirements met** counts the required competencies (those with a Want tag) scored 3–4, for example "7 of 9". It is shown beside the fit; the fit is evidence strength, not the share of requirements met.

**The label** is what the job's evaluation recommends, on every card, verdict and comparison:

| Label | Meaning | Rule |
|---|---|---|
| **Promising** | You meet the core requirements and the role matches your direct experience | Final fit 75% or more, with no critical gap, no required ask scored 2 and a fresh posting |
| **Stretch** | You meet the core competencies but lack some preferred skills, an industry or a confirmation | Final fit 60–74%; or 75%+ moved down by a critical gap, a required ask scored 2 or a stale posting |
| **Deprioritize** | A poor fit or a long shot | Final fit below 60%; any failed condition; or a Stretch moved down by a stale posting |

A critical gap is a required ask scored 0–1 or contradicted by dated records. A posting is stale when it is older than `stale_after_days` in the search criteria (21 days, three weeks, by default). A label moves down at most one level. The tool computes the label; copy it, never choose it. Whether a company is really hiring cannot be known from a posting, so no label claims it. The user may still choose to pursue any job.

The same asks, evidence ratings and documented adjustment always give the same result, in search and in Stage 1. Search drafts set `adjustment` and `adjustment_reason`, and `pipeline.py result` computes the same fields with the same engine. A later evaluation of the same job can change when a clarification or deeper evidence changes its inputs; name the changed inputs rather than changing the standard.

## Tool use

Render the job-description key through `job-search/tools/jd_ingest.py render DIR MAP --save tags.json`, which guards `tools/jd_key.py`; the artifact keeps the map and the verified selections. Where the adapter cannot run, use `jd_key.py render` and do not call the key source-verified.

For Stage 1, keep private `scores.txt` ratings for every tag, one `TAG SCORE [trait] [RECORD,...]` per line (for example `Want-1 3 NW-EXP-001,NW-OUT-001`; `Cond-1 pass`; `Want-4 0`), and a `groups.json` file when restatements are merged:

```json
{"delivery": ["Want-1", "Do-3"], "analytics": ["Want-2"], "optional": ["Nice-1"]}
```

```sh
python3 tools/jd_key.py assemble tags.json --scores scores.txt --groups groups.json --adjustment 0 --assessment-out assessment.json head.md key.md body.md > fit-check.md
```

Add `--stale` when the posting date is known and more than three weeks old. Omit `--groups` only when each selected ask is already a unique competency. Conditions are rated pass, fail or unknown in scores.txt and left out of groups. For a nonzero adjustment, add `--adjustment-reason "reason"`. `assemble` rejects record IDs that are not in the career record.

`shared-2` replaces the earlier Stage 1 formula (About and trait tags at half weight, nice-to-haves at full weight, bands at 80 / 70 / 60 with Pursue). Do not relabel an evaluation made under the earlier formula or overwrite it with a recalculated score.
