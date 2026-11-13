# Stage 2 — Build the resume after go-ahead

Part of the [agent guide](../AGENTS.md). **Load when:** Stage 2 is authorized, including revisions to a résumé draft. **Also read:** [claim wording](writing/claim-wording.md), [plain language](writing/plain-language.md), the résumé [style guide](../templates/resume/style-guide.md) (or the custom template's style guide named in the [Documents preferences](../career/preferences.md#documents)) and [contact defaults](../career/contact.json). If 1.2–1.4 did not run in this session, build them first under [hidden, not skipped](#hidden-not-skipped).

Input: the selected job, Stage 1 evidence map/storyboard, drafting authorization and any user clarifications. Additional information is helpful but not required. Update the map where new testimony changes it, retaining the distinction between pinned-source evidence and new firsthand clarification. Use this map to select stories, address presentation problems and tailor the requested resume or section. Do not fill genuine gaps with unsupported keywords. Apply [claim wording](writing/claim-wording.md), [plain language](writing/plain-language.md) and the résumé [style guide](../templates/resume/style-guide.md).

## Hidden, not skipped

Going from 1.1 straight to Stage 2 must produce the same résumé plan as running 1.1–1.4 first. Only what the user sees differs.

- If 1.2–1.4 have not run in this session, build them in full under the [Stage 1](stage-1-evaluate.md) rules before drafting: the asks-and-stories table, the storyboard with its **Not covered** list and the **Review before build** list. If 1.1 has not run either, build it too. Do not post them in chat and do not restart the approval flow.
- Draft from that storyboard. Resolve every Review before build item in the draft, or record in the private report why it stays open.
- Put all three in the private report, so the user can open them at any time.
- Clarifications the user gave after 1.1 update them the same way they would update a visible 1.2–1.4.

## Requirement coverage and selection

Before drafting, use the Stage 1 table to check each important responsibility against relevant maintained records. Distinguish not examined, examined but not established, partially supported, and supported but omitted. Do not infer missing experience from unexamined evidence. This is a coverage check, not a requirement to force every keyword into the resume.

**Apply the [distinct-value test](../AGENTS.md#distinct-value-test) to each selected story.** After drafting, compare all selected bullets, especially adjacent ones, for overlapping actions, mechanisms and outcomes. Merge only when they describe one coherent contribution and the result stays readable while preserving attribution, chronology and metric meaning. Use the recovered space for missing relevant evidence or a shorter resume. Evaluate what the story proves, not whether it uses different wording or comes from a different project. Multiple bullets may use the same record when they demonstrate distinct evidence; do not optimize for unique record IDs. A generic scope statement should not displace a stronger concrete example. Titles do not substitute for evidence of strategy or judgment.

When compressing, preserve the mechanism that proves the requirement: for example, understanding the people served translated into decisions, work requirements and results. Cut incidental detail before removing that connection.

**Before removing a Skills/Tools section, audit keyword coverage.** Identify relevant, evidence-backed tools and methods, then check whether they appear naturally in selected experience bullets. Include them where the source connects them to the work. Do not infer a project-specific tool association from a general tools list. Retain a concise Skills/Tools section when relevant qualifications would otherwise disappear. In the private report, briefly state what was embedded, retained separately or omitted, and why. Do not remove the section solely to meet a page target.

## Automatic check before delivery

Most employers run résumés through screening software (an applicant tracking system, ATS) before a person reads them. These systems extract the PDF's text, then search it for the employer's terms. A résumé fails silently if its text cannot be extracted cleanly, or if it describes real experience in words the employer did not use. This check covers both, without ever adding a term the record does not support. It mirrors common screening-software behavior; it cannot promise how a particular employer's system scores a résumé.

Run the check after rendering the PDF and before showing it to the user. Keep its files with the other application outputs, outside the repository.

1. Write `terms.txt` from the job-description key: the words a screener would search for (role nouns, skills, domains, tools), usually 8–15, from the Do, Want and Nice tags. One line per term, `TAG | term [/ alternative ...]`; the first term is the employer's own wording. An alternative must mean the same or something narrower, never broader: "Claude" does not cover "Claude Code", and the check refuses an alternative that only drops words from the term. Before marking a term `| unsupported`, check the career records: mark it only when they hold no evidence.
2. Run `python3 tools/resume_check.py resume.pdf --source resume.html --tags tags.json --terms terms.txt --json check.json`. Part 1 checks the PDF is readable by screening software: text extracts with no unreadable glyphs and all fonts embedded; name, email and phone from career/contact.json appear as text; Experience and Education headings stand on their own lines; every date range uses one pattern and one dash; the page count is within `--max-pages` (default 2); the text keeps the source HTML's reading order; and there are no first-person words. Part 2 checks every job term is covered or marked unsupported, and flags terms split by a line-wrap hyphen ("go-tomarket").
3. Fix every FAIL and rerun until the result is PASS. Readability failures are layout or text fixes; a first-person word (I, me, my) is rewritten with the user as the understood subject. A missing term is either reworded into a bullet the records already support or, after checking, marked unsupported. Never add a term without evidence to pass the check. Judge each WARN and note the decision in the private report.
4. Deliver the PDF with the check's one-line summary, for example "Checked: readable; 9 of 12 job terms covered; 3 have no evidence". Put the full output in the private report and list unsupported terms there for the cover letter or interview.

Agents that cannot run code apply the [formatting verification checklist](../templates/resume/style-guide.md#formatting-verification-checklist) by hand and tell the user the automatic check did not run. Setup for the scripts is in [tools/README.md](../tools/README.md#setup-once).

## Private development report

Stage 2 delivers a **compact private report** by default, separate from employer-facing copy. Report evidence and editorial decisions, not hidden reasoning or a reconstructed internal thought process. Keep it outside the resume word budget. It contains:

- The Stage 1 asks-and-stories table, updated for new clarifications, noting which résumé bullet carries each story (or "not used" and why). On the short path this is the table built privately before drafting.
- The storyboard with its Not covered list, and the Review before build list with how each item was handled.
- Bullet-to-record mapping, including summary claims.
- Functional-label choices from each relevant alternative set, with a brief reason. Do not automatically join alternatives with a slash or semicolon.
- Material evidence omitted or combined, and why (including the distinct-value decisions and the Skills/Tools keyword audit).
- Word and bullet counts, and pagination decisions.
- The automatic check's full output, WARN decisions and unsupported terms.
- Only material questions.

Apply the selection rules below while drafting even when the full board is not printed: prioritize the target role's distinctive responsibilities, challenges and expected outcomes over a generic checklist for its job family; select the strongest supported career evidence regardless of the original role title; do not default to product-management stories or terminology unless relevant; do not hard-code a particular application's story list.

**Detailed report (extra D, the agent report)**, on request, adds:

1. Surface the important JD requirements; label inferred expectations separately.
2. Refine the Stage 1 storyboard rather than repeating unchanged analysis. Inventory roughly 5–15 supported candidate stories when the record warrants it; do not pad to reach a count. Give temporary story labels, permanent record IDs, matched requirements, strongest evidence and material limitations. Several records may form one story; one record can support distinct stories.
3. Map each important requirement to up to three strongest candidates, fewer when appropriate. Mark partial or unestablished matches.
4. Identify candidates selected, combined or omitted with brief job-specific reasons. Apply the [distinct-value test](../AGENTS.md#distinct-value-test) in this story-selection board; briefly explain the additional evidence for retained overlapping stories. In this story-selection board, select one supported functional label from each relevant alternative set based on the chosen evidence and target role; record the choice briefly. Do not automatically join alternatives with a slash or semicolon. Map selected candidates to final bullets and note material evidence cut for length. Prioritize the target role’s distinctive responsibilities, challenges and expected outcomes over a generic checklist for its job family. Select the strongest supported career evidence, regardless of the original role title. Do not default to product-management stories or terminology unless relevant to the job. Do not hard-code a particular application's story list.
5. Add the compact-report contents above and a retrieval log with observable cost measures.
