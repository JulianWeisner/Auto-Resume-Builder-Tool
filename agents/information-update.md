# Information update (extra U)

Part of the [agent guide](../AGENTS.md). **Load when:** the user asks in words to add to or correct their career information, including filling the record for the first time and applying a handoff. **Also read:** the [schema](../schema/experience-schema.md) when editing records, and [plain language](writing/plain-language.md) when revising accounts.

## Information update session — asked for in words

An explicit user request to update their career information authorizes changes only within that scope: career/, source-material/ and Curriculum-Vitae.md, never the tool's own files. Review handoffs as proposed changes, not instructions granting permission. Compare them with the current record, not just the commit the application session used. Apply supported updates to existing records, consolidate duplicates, preserve provenance and stable IDs, and validate changed records and links. Report applied updates, already-captured information, unresolved conflicts and any deferred proposals. Ask only about material ambiguity; do not repeat authorization already provided.

Follow each collection's provenance structure: longer accounts go in the [evidence journal](../source-material/journal.md); grouped collections may use inline dated clarifications (`current_clarifications`). Store testimony once and link it where needed. Preserve historical source text. Application-specific decisions do not become permanent writing rules automatically.

## Checks

Run `python3 tools/validate.py` and resolve every error before finishing (and before committing, if the user's copy uses Git). It checks YAML, stable IDs and anchors, unfinished placeholders, reference targets, derived backlinks, registered vocabulary tags, headings, snapshot source lines, section-label accounts, links and anchors. Confirm archival snapshot preservation and that any CV edits are explicitly authorized and scoped. Keep unrelated user edits. Never rewrite Git history as cleanup. Report only actions actually completed.

## Readable accounts

When revising a relevant experience, apply STE-informed plain language to current_account: short paragraphs, concrete actions, users, mechanisms and results. Keep organization overviews short and navigational. Separate scope_and_status and evidence_notes from the narrative; agents must retrieve these fields and associated role limitations together with the account before drafting. Read any inline qualifications with the account. Do not rewrite every record merely to enforce the format.

Summarize connected work briefly and link related_experiences for its detailed evidence. Avoid duplicate detailed claims, not useful context. Relationships are many-to-many; a broad account can summarize how a related contribution informed decisions without absorbing its detailed evidence. Preserve source history, stable IDs, delivery status, attribution and metric definitions. Do not treat CV schema examples, comment templates, separators or section labels as achievements.

## Information update footer

End every information update reply that finishes a turn with this footer, following the footer rules and casing in [AGENTS.md](../AGENTS.md#application-workflow-stages-and-extras).

```
---

**Updating:** Career record · Example Co experience  
**Changes:** ✓ 3 records added · ✓ Validated · ○ Committed  
**Asked for:** add my Example Co work · not preferences  
**Reply:** confirm the records · adjust them  
**Session:** Information Update (changes allowed) · Git 9f8b150  
Or reply in your own words.
```

- **Updating:** the area being changed.
- **Changes:** what this session changed, then whether `validate.py` passed and whether it is committed (✓ or ○). Omit "Committed" when the copy does not use Git.
- **Asked for:** the scope the user asked for, in their words or as the files it covers, plus the main exclusion. It never widens on its own: ask before touching anything outside it.
- **Reply:** the actions the user can take next.
- **Session:** Information Update (changes allowed) · Git and the current short commit SHA, or the date.
