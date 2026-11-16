# Stage 2 — Build the resume after go-ahead

Part of the [agent guide](../AGENTS.md). **Load when:** Stage 2 is authorized, including revisions to a résumé draft. **Also read:** [claim wording](writing/claim-wording.md), [plain language](writing/plain-language.md), the résumé [style guide](../templates/resume/style-guide.md) (or the custom template's style guide named in the [Documents preferences](../career/preferences.md#documents)) and [contact defaults](../career/contact.json). If 1.2–1.4 did not run in this session, build them first under [hidden, not skipped](#hidden-not-skipped).

Input: the selected job, Stage 1 evidence map/storyboard, drafting authorization and any user clarifications. Additional information is helpful but not required. Update the map where new testimony changes it, retaining the distinction between pinned-source evidence and new firsthand clarification. Use this map to select stories, address presentation problems and tailor the requested resume or section. Do not fill genuine gaps with unsupported keywords. Apply [claim wording](writing/claim-wording.md), [plain language](writing/plain-language.md) and the résumé [style guide](../templates/resume/style-guide.md).

## Hidden, not skipped

Going from 1.1 straight to Stage 2 must produce the same résumé plan as running 1.1–1.4 first. Only what the user sees differs.

- If 1.2–1.4 have not run in this session, work through them under the [Stage 1](stage-1-evaluate.md) rules before drafting: check each requirement against the records, plan the stories, list what stays uncovered and the review-before-build items. If 1.1 has not run either, run it too. Do not post them in chat and do not restart the approval flow.
- Record the result compactly in `plan.md`, one line per item and no prose paragraphs:
  - **Storyboard:** each heading with its chosen functional title and dates, then one line per selected story naming the requirements it demonstrates, in the Stage 1 1.3 form.
  - **Not covered:** one line per important requirement no selected story covers, with where to address it.
  - **Review before build:** one line per item, with how the draft handles it or why it stays open.
  - **Titles:** the functional label chosen from each alternative set, with a one-line reason.
  - **Omitted or combined:** material evidence left out or merged, with a one-line reason, including the Skills/Tools audit.
  - **Check decisions:** each WARN decision and each term marked unsupported.
- Draft from that plan. Clarifications the user gave after 1.1 update it the same way they would update a visible 1.2–1.4.
- The full asks-and-stories table is written only when the user asks for it. The scores, the plan and the records hold everything it needs.

## Requirement coverage and selection

Before drafting, use the Stage 1 table to check each important responsibility against relevant maintained records. Distinguish not examined, examined but not established, partially supported, and supported but omitted. Do not infer missing experience from unexamined evidence. This is a coverage check, not a requirement to force every keyword into the resume.

**Apply the [distinct-value test](../AGENTS.md#distinct-value-test) to each selected story.** After drafting, compare all selected bullets, especially adjacent ones, for overlapping actions, mechanisms and outcomes. Merge only when they describe one coherent contribution and the result stays readable while preserving attribution, chronology and metric meaning. Use the recovered space for missing relevant evidence or a shorter resume. Evaluate what the story proves, not whether it uses different wording or comes from a different project. Multiple bullets may use the same record when they demonstrate distinct evidence; do not optimize for unique record IDs. A generic scope statement should not displace a stronger concrete example. Titles do not substitute for evidence of strategy or judgment.

When compressing, preserve the mechanism that proves the requirement: for example, understanding the people served translated into decisions, work requirements and results. Cut incidental detail before removing that connection.

**Before removing a Skills/Tools section, audit keyword coverage.** Identify relevant, evidence-backed tools and methods, then check whether they appear naturally in selected experience bullets. Include them where the source connects them to the work. Do not infer a project-specific tool association from a general tools list. Retain a concise Skills/Tools section when relevant qualifications would otherwise disappear. In `plan.md`, briefly state what was embedded, retained separately or omitted, and why. Do not remove the section solely to meet a page target.

## Build and check before delivery

Most employers run résumés through screening software (an applicant tracking system, ATS) before a person reads them. These systems extract the PDF's text, then search it for the employer's terms. A résumé fails silently if its text cannot be extracted cleanly, or if it describes real experience in words the employer did not use. The build and its check cover both, without ever adding a term the record does not support. The check mirrors common screening-software behavior; it cannot promise how a particular employer's system scores a résumé.

Build the PDF with one command; do not render PDFs, count pages or inspect page images by hand. Keep the build files with the other application outputs, outside the repository, in a folder that outlasts the session (on a personal computer, for example `~/Resumes/<company-role>/` or the repository's `output/` folder, which Git ignores; never a temporary folder such as `/tmp`), and name that folder in the reply. In a cloud session, also deliver the PDF in the conversation.

**Ready the environment once, before the first build.** Run `python3 tools/build_resume.py --check-setup`. It builds a small test résumé end to end and says READY only when that works. If it is not ready, run `python3 tools/build_resume.py --setup`: it installs pinned tools into a lasting per-user folder and reuses them on later runs. Keep setup and build commands on their own, not chained with other shell commands, so one approval covers each. If either needs permission (network, or starting a browser), ask the user once per capability with the exact command; after approval, continue through rendering, fixes and rebuilds without asking again.

The PDF comes only from `tools/build_resume.py`, starting from `templates/resume/resume.html` (or the custom template named in the [Documents preferences](../career/preferences.md#documents)). Never make it another way: no other PDF library (such as ReportLab), no renderer of your own, and no font, size or margin changes outside the template to make it fit; cut content instead. Without a clone, copy the [tool kit](../AGENTS.md#application-workflow-stages-and-extras) first. A PDF made any other way is not a résumé for delivery.

1. Write `terms.txt` from the job-description key: the words a screener would search for (role nouns, skills, domains, tools), usually 8–15, from the Do, Want and Nice tags. One line per term, `TAG | term [/ alternative ...]`; the first term is the employer's own wording. An alternative must be another way of saying the term (a synonym, abbreviation or narrower form), never broader and never a phrase that only shows evidence for it: "Excel" does not cover "Excel macros", and "used by Acme" is evidence of adoption, not a word for it. The check refuses an alternative that only drops words from the term, runs past four words, or adds evidence words such as "used", "by" or "for". Before marking a term `| unsupported`, check the career records: mark it only when they hold no evidence.
2. Write `sources.md`: one line per résumé bullet and summary claim, naming the records behind it, for example `Northwind · returns redesign → NW-EXP-002, NW-OUT-001`.
3. Run `python3 tools/build_resume.py resume.html --tags tags.json --terms terms.txt --snapshot fit-check.md tags.json scores.txt plan.md sources.md`. It renders the PDF, measures the layout (page count, a heading stranded at a page bottom, a near-empty last page), runs the automatic check and lists each problem with its fix. Add `--previews` only when a listed problem needs a look.
4. Fix each listed problem and rebuild until it prints **BUILD OK**. Layout: cut or shorten the lowest-value content when over the page target; wrap a stranded heading and its first entry in `<div class="keep">` instead of adding a manual page break. Check failures: a first-person word (I, me, my) is rewritten with the user as the understood subject; a missing term is either reworded into a bullet the records already support or, after checking, marked unsupported. Never add a term without evidence to pass the check. Judge each WARN and note the decision in `plan.md`.
5. On BUILD OK the build saves a `<name>-snapshot` folder beside the PDF with the decision files, the HTML, the PDF, the full check output, the tool versions and a manifest of hashes with the build time. Each passing build replaces it, so one application folder holds only the current résumé and its decisions; The user can delete the folder once they have applied (after the archive) or passed on the job. Deliver the PDF with the check's one-line summary, for example "Checked: readable; 9 of 12 job terms covered; 3 have no evidence", plus any open questions. Do not write a further report unless the user asks. Do not list selection choices (titles, lead stories, omissions) in chat; they belong in the reasoning report.

### When the build cannot run

A build that exits 2 prints `BUILD CANNOT RUN (kind)` and one fix: **missing** (run `--setup`), **not downloaded** (run `--setup`, or use installed Chrome), **blocked** (the browser exists but the session stopped it: ask the user once to approve the build command, then rerun it) or **failed** (rerun once, then `--check-setup`). Apply that fix before anything else; do not retry what cannot change the result.

Deliver a draft instead of a PDF only when recovery is unavailable (no shell, or the tool kit cannot be copied), refused, or still failing after the fix:

1. Start the reply with one line: "Résumé drafted; PDF not built: [reason and what was tried]".
2. Deliver the HTML with print steps: open it in Chrome, Print, Save as PDF, paper US Letter, scale 100%, headers and footers off.
3. Apply the [formatting verification checklist](../templates/resume/layout-reference.md#formatting-verification-checklist) by hand and keep the same decision files. Never call the résumé built, checked or ATS-checked, and give no "Checked:" line.
4. Give the one command that would fix it, usually `python3 tools/build_resume.py --setup` on the user's computer or in the environment's setup script.
5. In the footer, mark the stage "▸ Résumé drafted · PDF pending" instead of "✓ Résumé".

## Private development report

**By default, the build snapshot is the private record.** It holds the fit check, the tagged posting, the scores, `plan.md`, `sources.md` (the records behind each bullet and summary claim), `terms.txt` and the full check output. Chat shows only the PDF, the check's one-line summary and any open questions. Write no report unless the user asks. Write `plan.md` and `sources.md` so the reports can be built from them: in `plan.md`, start lines with `Source:`, `Storyboard:`, `Not covered:`, `Review before build:`, `Titles:`, `Omitted or combined:`, `Skills/Tools audit:` and `Check decisions:`; in `sources.md`, write `résumé line -> RECORD-ID, RECORD-ID`.

Two reports, each only on request, both compiled from the résumé's `<name>-snapshot` folder so they record what was decided when the résumé was built. Never reconstruct reasons the snapshot does not hold.

**Proof report** ("proof report"): can the résumé be trusted? Run `python3 tools/proof_report.py <name>-snapshot` and deliver the `proof.html` it writes; do not write it by hand. It shows each résumé line with its records' current wording and limits, the fact confirmations, term evidence, the automatic check, and the sources and build log. It takes seconds and no drafting.

**Reasoning report** ("reasoning report"): why this résumé? Written by the agent, in plain language, labeled "Compiled after the résumé from the build snapshot of [time]"; list any clarifications the user gave after that build separately and note that the delivered résumé predates them. It contains:

1. **Assessment:** verdict, fit and the drivers, briefly.
2. **Requirements and stories:** one table; each row starts with the requirement's quoted wording (from `tags.json`), then evidence strength in words (same work, same work in another setting, related, thin, none), the story chosen and the résumé line that carries it, or "not used" and why. Show each requirement with thin or no evidence in its own row.
3. **Story choices:** only real decisions: chosen over what, and why (including the distinct-value test).
4. **Storyboard, titles and chronology:** order, the functional label chosen from each alternative set and why. Do not join alternatives with a slash or semicolon.
5. **Gaps and how to cover them:** unsupported terms and Not covered asks, each marked for the cover letter or the interview.
6. **Open questions:** only material ones.

"agent report" means both reports; "full evaluation" after a résumé means the reasoning report.

Apply the selection rules below while drafting even when the full board is not printed: prioritize the target role's distinctive responsibilities, challenges and expected outcomes over a generic checklist for its job family; select the strongest supported career evidence regardless of the original role title; do not default to product-management stories or terminology unless relevant; do not hard-code a particular application's story list.

**Detailed report (extra D)**, on explicit request, extends the reasoning report:

1. Surface the important JD requirements; label inferred expectations separately.
2. Refine the Stage 1 storyboard rather than repeating unchanged analysis. Inventory roughly 5–15 supported candidate stories when the record warrants it; do not pad to reach a count. Give temporary story labels, permanent record IDs, matched requirements, strongest evidence and material limitations. Several records may form one story; one record can support distinct stories.
3. Map each important requirement to up to three strongest candidates, fewer when appropriate. Mark partial or unestablished matches.
4. Identify candidates selected, combined or omitted with brief job-specific reasons. Apply the [distinct-value test](../AGENTS.md#distinct-value-test) in this story-selection board; briefly explain the additional evidence for retained overlapping stories. In this story-selection board, select one supported functional label from each relevant alternative set based on the chosen evidence and target role; record the choice briefly. Do not automatically join alternatives with a slash or semicolon. Map selected candidates to final bullets and note material evidence cut for length.
5. Add the proof report and a retrieval log with observable cost measures.
