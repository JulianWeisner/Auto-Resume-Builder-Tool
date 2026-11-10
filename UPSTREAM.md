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
| agents/screening-check.md | Stage 1 job-description key step and Stage 2 "Requirement coverage" and "Automatic check before delivery" | Extracted into one standalone module so the check works before the full workflow is ported |
| AGENTS.md | distinct-value test, routing, scripts | Routing table limited to modules that exist here |
| career/preferences.md | — | New "Documents" section: template, page length, paper size, optional signature |
| tools/jd_key.py | same | Unchanged |
| tools/resume_check.py | same | Contact read from career/contact.json |
| tools/current_view.py | same | Collections discovered automatically under career/; organization-specific note removed |
| tools/validate.py | same | Organization-specific navigation checks generalized to "## ID — Title" headings; CV snapshot found by revision; new checks for anchors, unfinished placeholders and unregistered vocabulary tags; empty skeleton passes |
| tools/agent_bundle.py | same | Task names read from the routing table instead of a fixed list |
| tools/README.md | new | Setup and script overview |

**Not ported yet:** Stage 1, Stage 2 and Stage 3 modules, handoff, archive, footer, evaluations procedure.
