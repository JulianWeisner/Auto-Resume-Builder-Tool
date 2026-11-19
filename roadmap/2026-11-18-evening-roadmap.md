# Roadmap snapshot — November 18, 2026 (evening)

[Roadmap](../ROADMAP.md) · **Status: snapshot, not a commitment.** Each roadmap is a new, dated file. Earlier roadmaps are not rewritten, so the history shows how the plan changes. The previous snapshot is [this morning's](2026-11-18-roadmap.md). This file describes the tool's development; agents do not treat it as operating instructions.

## What changed since this morning

Today's merged changes bring the product level with the upstream personal tool for search, the queue and the tracker:

- **Shared evaluation standard:** one scoring engine and one Promising / Stretch / Deprioritize label for search and Stage 1.
- **Application tracker:** every archived application, its replies and a status worked out from dated events.
- **Career informed search and the application queue**, with **HiringCafe** as the first job source and setup steps for each AI tool. Location checks now measure from the user's own center anywhere in the US.
- **README opening:** the AI tool is the interface; the repository holds the record and the rules.
- **"Recalled working figures"** became a preference question instead of a fixed rule.

## Status key

✓ built · ◐ partial · ○ planned · ◇ idea · — not in that track's scope

The **Product** column is this repository, Auto-Resume-Builder-Tool: the free, person-neutral tool that users copy. The **Upstream** column is the upstream personal tool, the private project where features are built and used on real applications first, then ported here ([UPSTREAM.md](../UPSTREAM.md)). A status in *italics* changed today; the morning status follows in brackets.

## The elements

### 1. Personal career database builder

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Record skeleton and schema | ✓ | ✓ | Empty pages and record templates in `career/` |
| One tag vocabulary | ✓ | ◐ | `career/vocabulary.md` |
| Guided onboarding | ◐ | — | Agent guidance exists; scripted flow to come |
| Preference prompts | ✓ | ◇ | `career/preferences.md`; adds the "recalled working figures" question |
| Answer bank | ✓ | ◐ | |
| Gap-filling through handoffs and information updates | ✓ | ✓ | |
| Validator | ✓ | ✓ | `tools/validate.py` |

### 2. Career informed search

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Search criteria and capability profile | *✓* (○) | ✓ | "Set up my search" fills `career/search-criteria.yaml`; the profile is `career/capability-profile.yaml`. Both are the user's data |
| Search runs and intake | *✓* (○) | ✓ | `job-search/` toolkit and [runbook](../agents/job-search.md); checked live on the sample person |
| HiringCafe connected in each AI tool | *✓* (new) | — | [Setup page](../job-search/hiringcafe-setup.md); `.mcp.json` and `.gemini/settings.json` offer it in the folder |
| Conditions from the user's own center | *✓* (new) | — | `tools/conditions.py` with every US place; upstream keeps one fixed center |
| Sources that work with any job provider | *◐* (○) | ◐ | HiringCafe first; readers accept several response formats; a new source needs a new reader |
| Job-alert cards | ◇ | ◇ | |
| URL integration | ◇ | ◇ | Paste or open a posting link to start |

### 3. Job match analysis

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Shared evaluation standard | *✓* (new) | ✓ | [agents/evaluation.md](../agents/evaluation.md), `tools/evaluation.py` |
| Fit check with weighted scoring | ✓ | ✓ | |
| Conditions as a pass/fail filter | ✓ | ✓ | Now the shared checker in both workflows |
| Verdict card | ✓ | ✓ | |
| Full evaluation | ✓ | ✓ | |
| Story index helper | ✓ | ✓ | `tools/current_view.py --index` |
| Batch triage | *◐* (○) | ◐ | Search gives review cards in batches. Open: several pasted postings still get the Stage 1 comparison table, not cards |

### 4. Tailored résumé generation

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Résumé outline (storyboard) | ✓ | ✓ | |
| Generation and one-command build | ✓ | ✓ | `tools/build_resume.py` |
| Templates | ✓ | ✓ | |
| Custom template builder | ✓ | — | `templates/custom/` |
| Screening-software check | ✓ | ✓ | |
| Reasoning and proof reports | ✓ | ✓ | |

### 5. Tailored cover letters and application answers

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Cover letters | ✓ | ✓ | |
| Portal answers from the answer bank | ✓ | ✓ | |
| Repeated written answers | ○ | ○ | "Why this company?", "Tell us about yourself" |

### 6. Application submission (may or may not be built)

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Portal filling with approval before every submission | ◇ | ◇ | |
| Follow-up reminders | ◇ | ◇ | |

### 7. Application tracking and insights

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Archive of job descriptions and files sent | ✓ | ✓ | |
| Log replies | *✓* (◐) | *✓* (◇) | Tracker events; employer emails saved unedited |
| Status tracker and visualizer | *✓* (◇) | *✓* (◇) | "Show my applications"; the queue board |
| Analysis of jobs applied to and replies received | ◇ | ◇ | The events are in place; it needs logged replies first |

### 8. Interview preparation (may or may not be built)

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Key stories | ◇ | — | Product-line expansion, built here only |
| Recall-first rewrite | ◇ | — | |
| Read to refresh | ◇ | — | |
| Mock interview | ◇ | — | |

## Experience layer

Spans career informed search, job match analysis and résumé generation.

| Component | Product | Upstream | Notes |
|---|---|---|---|
| Application queue | *✓* (◇) | *✓* (◇) | Interested / Pass on review cards, then a board, best fit first, with Build résumé and Drop. Built as cards, not swipes |
| Screens in every AI tool | *✓* (new) | ✓ | Drawn in a Claude chat, served in the browser on the user's computer (`tracker.py serve`), or sent as a file from a cloud session |
| Shortcuts: queue, drop, update queue | *✓* (new) | ✓ | Claude Code and Gemini CLI use `/`, Codex uses `$` |

## Foundation (inherent, not a user element)

| Part | Product | Notes |
|---|---|---|
| Evidence rules: every claim traces to the record | ✓ | [AGENTS.md](../AGENTS.md) |
| Writing guides (plain language with ASD-STE100, claim wording) | ✓ | `agents/writing/` |
| Works with any AI tool | ✓ | AGENTS.md, CLAUDE.md, GEMINI.md, and the shortcuts for each tool |
| Privacy guard: no one's data ships | ✓ | `tools/check_skeleton.py`; now also covers saved searches and tracker events |
| Setup, sample person and tests | ◐ | Scripted runs pass; next is a search on the sample person driven end to end by an AI agent |
| Update delivery from upstream to users | ○ | The update command covers the new folders; release rhythm and how users learn of an update are open |
| License and template repository | ○ | Open: license not chosen; public template repository planned |

## Parity gaps and loose ends

| Item | Status | Notes |
|---|---|---|
| `add-event` date defaults to today | ○ | Upstream added it in its PR #42 after the queue port |
| Search judgment tests on the sample person | ○ | Upstream's calibration set and saved regression judgments cite the upstream owner's records, so they were not ported |
| Batch triage for pasted postings | ○ | See element 3 |

## Out of scope

- **Offer stage** (offer comparison, negotiation): not in the near or short term.
