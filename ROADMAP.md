# Roadmap

**Status: working plan, not a commitment.** Recorded November 9, 2026. This file describes the tool's development; agents do not treat it as operating instructions.

## What this is

A personalizable version of a résumé-and-application tool that is being built and used on real applications in a separate, private project (the "upstream personal tool"). Features mature there first, then move here in a person-neutral form, at irregular intervals. Features only this product needs (onboarding, interview preparation) are built here.

## Principles

- **No one's data ships.** This repository holds the tool and an empty skeleton only. An automatic check enforces it.
- **Any AI tool.** One rulebook ([AGENTS.md](AGENTS.md)) in plain Markdown, Python scripts with minimal dependencies, no features tied to one AI product.
- **Users own their copy.** Private by default, updated by pulling tool files only.
- **The evidence rules never loosen for speed.** Every claim traces to the user's record.
- **The skeleton is the head start.** New users get the full organizational structure, so they fill pages instead of designing a database.

## Phases

| Phase | What | Status |
|---|---|---|
| 0 | Repository boundary: privacy and skeleton guard, upstream port log | ✅ This version |
| 1 | Career-record skeleton: index, story, preferences, vocabulary, contact, collections, record templates, source material, archive conventions, schema reference | ✅ This version |
| 2 | Port the application workflow ("Skateboard"): fit check and verdict card, full evaluation, hidden-not-skipped, résumé build, automatic résumé check, footer, handoff into an information update session | ○ Next |
| 2a | Port the scripts, made collection-agnostic: current view (reads any collection the index lists), validator, job-description key, résumé check (contact from career/contact.json), agent bundle for chat tools without file access | ○ With phase 2 |
| 3 | Fictional sample person and proof run: a small made-up career used as test data, and one full run from posting to checked PDF | ○ With phase 2 |
| 4 | Guided onboarding: CV import script, chronological story prompts, example-driven recall prompts, preference prompts, validation at the end | ◐ Agent guidance exists in AGENTS.md; scripted flow to come |
| 5 | "Scooter" parity as it matures upstream: cover-letter template and style guide, answer-bank structure, repeated portal answers | ○ As upstream ships |
| 6 | Interview preparation (product-line expansion): key stories from the résumé, recall-first rewrite compared with records, optional read-to-refresh, mock interview | ◇ Idea |
| Later | Batch triage, job-alert cards, swipe to build, portal filling with approval, archive analysis | ◇ Follow upstream |

## Open decisions

- **License.** The tool is free; a license (for example MIT) is not chosen yet.
- **Repository visibility.** Public, marked as a GitHub template repository, so others can create private copies.
- **How updates flow from the personal tool.** Not designed yet. Today: features are ported by hand (logged in UPSTREAM.md), and users pull tool files with the git commands in the README. Open questions: a release or changelog rhythm, a script that updates only tool files, and how users learn an update exists.

## Lessons carried over from upstream

- Use **one tag vocabulary from day one**: upstream ended up with two (coded IDs and free text), which blocks a reliable story index.
- Give every record a **title**: untitled grouped records are harder to index.
- **Hidden, not skipped:** a shorter path does the same work and only shows the user less.
