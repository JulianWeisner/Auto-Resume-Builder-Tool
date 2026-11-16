# Upstream port log

Features in this tool are ported from a private personal project where they are first used on real applications. This log records what was ported, from which upstream revision, and how it changed. Personal data is never ported: only structure, rules, scripts and templates, rewritten in a person-neutral form.

Each entry lists: date · upstream revision (short SHA) · what was ported · what was generalized · what was deliberately left out.

## 2026-11-09 · upstream 01bfec7 · career-record skeleton

**Ported as structure (empty pages with guidance):**

| Here | Upstream source | Changes |
|---|---|---|
| career/README.md | career index | Generic collections (experience, education, additional); empty locator table |
| career/story.md | career story | Section pattern only |
| career/preferences.md | goals and preferences | Section headings, recording pattern, upstream roadmap's preference prompts broken into single short questions per topic; application-answer table with every answer "Not recorded" |
| career/vocabulary.md | vocabulary section of the schema | Moved to its own page; empty; one vocabulary from the start |
| career/contact.json | resume contact defaults | Moved from templates/ into the user's data area; all values empty |
| career/{experience,education,additional}/records.md | grouped collections | Empty, with guidance |
| career/_templates/ | record formats in grouped and organization collections | Blank YAML for role, experience, outcome, education, project, formal and functional roles |
| schema/experience-schema.md | experience schema | Rewritten as a general reference; organization-specific IDs, merge history and import counts removed |
| source-material/ | source index, CV snapshot, journal, document extracts | Empty, with conventions |
| applications/README.md | archive conventions | Generic; updates.md reply logging made explicit |
| AGENTS.md | AGENTS.md core sections | Authority, evidence and truthful writing kept; upstream's application and maintenance modes become application and information update sessions (the product has no maintenance of the tool from inside a user's copy); interviewing rule: one bite-sized question at a time; workflow stages, footer and routing deferred to phase 2; new "Filling the career record" section from the roadmap's onboarding notes |
| START.md | START.md | Rewritten for a new user: fill the record first; application flow marked as coming |

**Not ported yet:** agents/ modules, tools/ scripts, résumé and cover-letter templates, evaluations procedure (templates and scripts followed on 2026-11-10, below).

**Never ported:** career records, source material, applications, the CV, contact values, preferences content, evaluations results.

## 2026-11-10 · upstream 01bfec7 · documents, writing guides and scripts

| Here | Upstream source | Changes |
|---|---|---|
| templates/resume/ | templates/resume/ (v9 layout) | HTML layout unchanged; personal signature made optional with placeholder labels; style guide generalized (consulting presentation via `presentation_note`, contact from career/contact.json, A4 noted, screening-software safety rules grouped); PDF and preview re-rendered from placeholders |
| templates/cover-letter/ | templates/cover-letter/ | Name and signature replaced with placeholders; opening draws on preferences' Motivation section; PDF and preview re-rendered |
| templates/custom/README.md | new | Agent prompt for building a template from the user's example résumés: design criteria, information hierarchy, screening-software risks, build and test |
| templates/README.md | new | Index; which template is used; tool versus user files |
| agents/writing/plain-language.md | same | Name removed; short explanation of ASD-STE100; inflated-word examples added |
| agents/writing/claim-wording.md | same | Personal consulting-name rule replaced by `presentation_note`; employer-specific example made generic; weak/strong bullet table added |
| agents/screening-check.md | Stage 1 job-description key step and Stage 2 "Requirement coverage" and "Automatic check before delivery" | Extracted into one standalone module so the check works before the full workflow is ported; folded back into agents/stage-2-resume.md on 2026-11-10 (second entry) |
| AGENTS.md | distinct-value test, routing, scripts | Routing table limited to modules that exist here |
| career/preferences.md | — | New "Documents" section: template, page length, paper size, optional signature |
| tools/jd_key.py | same | Unchanged |
| tools/resume_check.py | same | Contact read from career/contact.json |
| tools/current_view.py | same | Collections discovered automatically under career/; organization-specific note removed |
| tools/validate.py | same | Organization-specific navigation checks generalized to "## ID — Title" headings; CV snapshot found by revision; new checks for anchors, unfinished placeholders and unregistered vocabulary tags; empty skeleton passes |
| tools/agent_bundle.py | same | Task names read from the routing table instead of a fixed list |
| tools/README.md | new | Setup and script overview |

**Not ported yet:** Stage 1, Stage 2 and Stage 3 modules, handoff, archive, footer, evaluations procedure (ported below, except evaluations).

## 2026-11-10 (second) · upstream 01bfec7 · application workflow modules

Module names, section headings and stage, extra and footer structure match upstream, so later ports can be compared file for file.

| Here | Upstream source | Changes |
|---|---|---|
| agents/stage-1-evaluate.md | same | Scoring, weights (condition tags excluded; About and trait tags at half weight), fit bands (80 / 70 / 60), ±5-point judgment, verdict card, asks-and-stories table, storyboard and review before build kept word for word. Name replaced by "the user"; employer-specific examples replaced with generic ones; current_view.py named as the first read |
| agents/stage-2-resume.md | same | Kept, with the screening-software explanation and resume_check's part 1 checks from agents/screening-check.md folded into "Automatic check before delivery"; custom template style guide allowed; benchmark section removed |
| agents/stage-3-copy.md | same | Name removed; salary left blank unless the user records or gives a figure; custom cover-letter template allowed |
| agents/handoff.md | same | "Repository update" becomes "record update"; applying a handoff is an information update |
| agents/archive.md | same | Git steps conditional on the user's copy using Git; new "Logging replies" section for the archive-analysis idea |
| agents/information-update.md | agents/maintenance.md (extra G) | Renamed extra U; scope limited to the user's data, never tool files; organization-specific provenance and validator notes generalized |
| AGENTS.md | Application mode, Tracking new details, Application workflow (stages, extras, source continuity, transitions, footer, casing, handoff offer), Routing, Working style | Ported; agent names become session names (Application, Information Update); footer label "Tool Mode" becomes "Session"; source continuity works with or without Git; routing adds the custom-template task |
| tools/agent_bundle.py | same | Task names taken from the routing table (stage-1, stage-2, stage-3, d, h, a, u, template), matching upstream's |
| START.md | START.md | Upstream's three-reply journey, reasoning view, "things you can say" table and two kinds of session, adapted |

**Not ported:** evaluations/ (benchmark procedure for developing the tool; not needed by users).

## 2026-11-13 · upstream 29e0121 (PRs #13–#21) · build, reports, conditions and setup

| Here | Upstream source | Changes |
|---|---|---|
| tools/build_resume.py | new | One-command render, layout measurement, check and snapshot; `--setup` and `--check-setup`. Contact read from career/contact.json; the readiness test uses placeholders while that file is empty; the approval prompt asks "the user" |
| tools/resume_check.py | same | Python PDF reader fallback and the shared tool environment; header-only date check; stricter term alternatives. Contact path changed; employer example replaced |
| tools/proof_report.py | new | Name removed |
| tools/current_view.py | same | Upstream `--search`, `--index` and `--ids … --related` merged into the product's automatic collection discovery; result cue words generalized; roles with start/end fields show dates in the index |
| tools/jd_key.py | same | Unchanged: conditions take pass, fail or unknown |
| tools/agent_bundle.py | same | `d <stage>` added to the product's routing-table task names |
| tools/test_build_resume.py, tools/test_current_view.py | same | Rewritten to run on a temporary copy of the new sample person instead of upstream's own records; a test that the sample validates |
| examples/sample-person/ | new | A made-up career (grouped and organization collections, limits, outcomes, a title progression, conditions in preferences) and a sample posting |
| tools/validate.py | same | Runs without AGENTS.md (for the tests) |
| tools/check_skeleton.py | — | Allows the fictional 555-01xx phone range used by the sample |
| agents/stage-1-evaluate.md, agents/stage-1-full-evaluation.md | same | Re-ported: conditions as a pass/fail filter with a Conditions line on the card; 1.2–1.4 split into their own module. Name and personal examples replaced |
| agents/stage-2-resume.md | same | Re-ported: plan.md, build and check, when the build cannot run, build snapshot as the private record, reasoning and proof reports. Screening-software explanation kept; custom template allowed; benchmark removed |
| agents/archive.md, applications/README.md, agents/writing/plain-language.md | same | Snapshot and reports archived; two plain-language bullets |
| agents/information-update.md | maintenance.md product-agent footer | The information update footer moves here, as upstream moved its product-agent footer |
| AGENTS.md | same | Tool kit without a local copy, one build path, PDF-pending footer state, reasoning and proof report options, aliases, read only the current step's modules, `d <stage>` bundles, current_view helpers |
| templates/resume/ | style-guide.md, layout-reference.md, resume.html, README.md | Style guide split into guide and layout reference; `.keep` class; title progression and presentation preferences, generalized |
| career/preferences.md, schema/experience-schema.md | upstream's personal Résumé presentation preferences and its employer roles guidance | Generalized into a "Résumé presentation" question bank (title progression, credentials always or by relevance, years-of-experience counted from a stored start date and never stored as a number) and a schema rule for title progression |
| START.md, README.md, tools/README.md | START.md, README.md | Setup section, conditions on the card, the two reports, aliases; tests and sample documented |

**Not ported:** evaluations/ (timing baseline, story-index comparison); upstream's README rewritten as a personal map; record, journal and source-coverage changes.
