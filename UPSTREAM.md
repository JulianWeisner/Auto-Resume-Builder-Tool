# Upstream port log

Features in this tool are ported from a private personal project where they are first used on real applications. This log records what was ported, from which upstream revision, and how it changed. Personal data is never ported: only structure, rules, scripts and templates, rewritten in a person-neutral form.

Each entry lists: date · upstream revision (short SHA) · what was ported · what was generalized · what was deliberately left out.

## 2026-11-09 · upstream 01bfec7 · career-record skeleton

**Ported as structure (empty pages with guidance):**

| Here | Upstream source | Changes |
|---|---|---|
| career/README.md | career index | Generic collections (experience, education, additional); empty locator table |
| career/story.md | career story | Section pattern only |
| career/preferences.md | goals and preferences | Section headings, recording pattern, preference prompts from the roadmap; application-answer table with every answer "Not recorded" |
| career/vocabulary.md | vocabulary section of the schema | Moved to its own page; empty; one vocabulary from the start |
| career/contact.json | resume contact defaults | Moved from templates/ into the user's data area; all values empty |
| career/{experience,education,additional}/records.md | grouped collections | Empty, with guidance |
| career/_templates/ | record formats in grouped and organization collections | Blank YAML for role, experience, outcome, education, project, formal and functional roles |
| schema/experience-schema.md | experience schema | Rewritten as a general reference; organization-specific IDs, merge history and import counts removed |
| source-material/ | source index, CV snapshot, journal, document extracts | Empty, with conventions |
| applications/README.md | archive conventions | Generic; updates.md reply logging made explicit |
| AGENTS.md | AGENTS.md core sections | Authority, evidence, truthful writing and the two kinds of session kept; workflow stages, footer and routing deferred to phase 2; new "Filling the career record" section from the roadmap's onboarding notes |
| START.md | START.md | Rewritten for a new user: fill the record first; application flow marked as coming |

**Not ported yet:** agents/ modules, tools/ scripts (current_view, validate, jd_key, resume_check, agent_bundle), résumé and cover-letter templates, evaluations procedure.

**Never ported:** career records, source material, applications, the CV, contact values, preferences content, evaluations results.
