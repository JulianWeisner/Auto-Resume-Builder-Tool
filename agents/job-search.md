# Career informed search

Part of the [agent guide](../AGENTS.md). **Load when:** the user asks to find, screen or choose jobs ("find me 10 jobs", "more cards", "update queue"). **Also read:** `career/search-criteria.yaml`, `career/preferences.md`, `career/capability-profile.yaml`, [search screening](../job-search/scoring.md) and [the shared evaluation standard](evaluation.md). Use the [toolkit README](../job-search/README.md) for commands and formats, not as a second operating policy. Do not load résumé modules or application archives for search.

The search works the same in every AI tool. The job postings come from HiringCafe, which the user connects to their AI tool once ([HiringCafe setup](../job-search/hiringcafe-setup.md)). Every rule below holds whichever tool runs it.

## Before the first search

Check these three things in order, and stop at the first one that is missing.

1. **HiringCafe is connected.** Look for its `search_jobs` and `get_job_details` tools in this session. If they are not there, say so in one line and give the user the steps for their AI tool from [HiringCafe setup](../job-search/hiringcafe-setup.md). Never invent postings, and never fill a search from memory or a general web search.
2. **The search criteria are filled.** `career/search-criteria.yaml` needs a `center` and `radius_miles`, at least one role family and the other conditions. If they are empty, offer to set up the search. Setting it up is an [information update](information-update.md) the user asks for in words ("set up my search"): interview them one question at a time ([Interviewing the user](../AGENTS.md#interviewing-the-user)), starting from what `career/preferences.md` already says. Ask where they search from and how far they will travel, which workplace types they accept, how much travel is fine, the lowest pay they would consider (or none), and the job titles they want, grouped into two to five families. Write the answers in `career/search-criteria.yaml` and, where the preferences do not hold them yet, in `career/preferences.md`. The [sample person's criteria](../examples/sample-person/career/search-criteria.yaml) show a filled file.
3. **The capability profile exists and is current.** If `career/capability-profile.yaml` is missing, offer to build it (also an information update): copy [the template](../career/_templates/capability-profile.yaml), list what the records positively support with their IDs and limits, set `career_commit` to the current commit, and run `pipeline.py check-profile`. Refresh it when `check-profile` warns that records changed.

## Boundaries

Search is read-only career work. Write run outputs outside Git (for example `output/search/<run-id>/`). Do not submit applications or contact employers. "Update queue" (or "save the run") authorizes committing only that run folder under `job-search/runs/` and the new event files it writes in `tracker/events/`; it does not authorize tool or career-record edits. Stage 1 and résumés begin only for selected jobs. Do not ask the user to qualify every listing or decide every card.

## Run discipline

- **Cards, not postings.** The number the user gives ("10 cards") is review cards: Promising and Stretch both count. The run fetches a first batch of 1.5× that, tops up in batches until the cards are reached, and never fetches more than 3× in total. Without a number, use `target_cards` in the search criteria.
- **Batches and progress.** Evaluate about five postings at a time. After each batch, report the status line, for example "6 of 10 cards ready · 9 of 15 fetched postings evaluated", and continue from the first unfinished job. If you must stop, the reply leads with that line, the step and the reason.
- **No reuse of earlier runs.** Never import fits, labels or ratings from an earlier run or chat. Each run evaluates its own postings under the current rules. An earlier card is not evidence for a new one.
- **Resuming.** A run resumes on the commit it was frozen on. Say which commit that is. If the repository has changed since, say so and offer a new run instead: ingestion and scoring fixes do not apply to postings already frozen.

## One workflow in every AI tool

1. **Prepare.** Record the commit you work from (full SHA; without Git, the date and "no Git") and the user's local run date. Install only Python 3 and `job-search/requirements.txt` for search (`python3 tools/build_resume.py --setup` covers it). Keep a unique run ID and folder; never overwrite a frozen manifest.
2. **Plan.** Run `pipeline.py plan --target N -o RUN/plan.json`, where N is the number of review cards the user names; it records the first batch and the fetch cap, and searches from the criteria's `center` and radius. Use the saved criteria; preferences win where they differ. Include every planned query, local and remote. Do not add salary or department filters during discovery. Missing pay must survive to L1.
3. **Search and save.** Inspect the HiringCafe tools actually available. Different connections may use different argument shapes, names and response formats; support them without declaring one obsolete. Pass the planned criteria using the exposed arguments. Some connections filter by when HiringCafe fetched a posting, not when it was posted; the candidates step filters by posted date, so record the difference rather than treating returned results as recent. Save each original response as `RUN/searches/<plan id>.json` or `.md`, replacing `:` with `__`. The JSON envelope in the README preserves the actual request as well as its response. If the AI tool offers a readable transcript, that remains supported. Follow display rules the connector states, but keep its discovery displays apart from the scored review cards.
4. **Ingest searches.** Run `hiringcafe.py searches INPUT RUN`. It preserves sources, parses supported formats and records receipts. Read changed or unknown filter checks. Correct materially wrong interpretations and rerun before selection, or record the limitation plainly. A response reporting ten jobs cannot become zero; an unsupported or partial response stays unresolved. Never rewrite a response to make a parser pass, invent listings or change the tools during a search.
5. **Select.** Run `pipeline.py candidates RUN --run-date DATE` for the first batch. Fetch its selected IDs, preserving the reasons and all occurrences. The code filters age and title before removing duplicates and takes jobs from each family in turn. Missing locations do not prove that different IDs are duplicates. Do not swap candidates by preference. Duplicates and failed fetches simply count against the batch; top-ups make up the cards.
6. **Fetch and ingest details.** Save original detail responses under `RUN/details/<job id>.json` or `.md`; run `hiringcafe.py ingest-raw RUN/details RUN`. Alternatively use transcript `extract`. Both preserve original responses and create JD artifacts. Confirm extracted travel and deadline text against the posting. A description delivered as one long paragraph is split into sentence blocks at ingestion, so each ask can be tagged; a provider description under 25 words is marked `insufficient` and stops at L1 like a truncated one ([JD ingestion](../job-search/jd-ingestion.md)). For truncated descriptions, use the employer's own posting when available. Do not score snippets or guess missing text. One unresolved response must not erase successful intake.
7. **Freeze and screen.** Run `pipeline.py freeze RUN/jobs.json --run-id ID --run-date DATE --commit SHA -o RUN/manifest.json`. This pins the L1 rules (the shared [conditions](evaluation.md#conditions) from `career/search-criteria.yaml`, posting age and the pay floor) and posting-input hashes. `pipeline.py screen` remains available for inspecting conditions; `result` also computes L1 automatically. L1 failures cannot pass through as scored eligible jobs. Unknown conditions remain visible as needs verification. Posting age uses the posting date, not the provider's fetch date.
8. **Interpret and evaluate.** Apply [the shared evaluation standard](evaluation.md) and [search screening](../job-search/scoring.md). Render the complete JD selection and skip map with `jd_ingest.py`; keep every selected tag when merging restatements. Draft requirements supply `source_tags`, a source-verified primary quote and `coverage.map_sha256`. Every selected tag is mapped once; only jobs stopped at the L2 screen may defer remaining tags, with reasons, under `coverage.deferred`. Use the capability profile, retrieving targeted current records and their limits for gaps or uncertain scope. Explicit mandatory asks carry `mandatory_basis: explicit`. Responsibilities and inferred concerns cannot become mandatory just because the requirements section is short. Stop at L2 when knockout rules apply; keep the reason and no fit. For survivors, separate fit, eligibility and application confidence, then write the job-first card. Never infer a capability the records only touch.
9. **Submit each result.** Write the agent's judgments to a draft and run `pipeline.py result DRAFT --run-dir RUN`. Invalid results are not written. L1 recomputation can turn a proposed score into an old-posting error or a condition exclusion. A Cond requirement you mark `fail` from the posting text (with a source-verified quote) also excludes the job, as Stage 1 deprioritizes it; mark `unknown` when the posting leaves it open. Repeat from the first unfinished job on resume.
10. **Top up.** When every fetched posting has a result, run `pipeline.py top-up RUN`. If it returns `fetch`, fetch and ingest those IDs, run `pipeline.py freeze RUN/jobs.json --run-id ID --run-date DATE --commit SHA --add -o RUN/manifest.json`, evaluate them, and run `top-up` again. If it returns `none`, the run is done: the card target is reached, the search results are exhausted or the 3× fetch cap is reached. Report which. The code chooses each batch; never add or swap jobs by hand.
11. **Deliver.** Run `assemble`, `validate --artifacts`, then `cards`. Use the status code's result. The run is complete when the card target is reached or `top-up` reports the results exhausted or the cap reached; say so when it ends short of the target. Do not describe a structural pass as a judgment that every evaluation is right, or as full coverage of the market. Deliver the cards, a count by label (Promising, Stretch, Deprioritize) and material limitations. A run without a validated cards page is not finished: say so in the first line, name the step where work stopped (for example "requirement mapping, 0 of 30 jobs evaluated") and report `pipeline.py status`. Never describe a partial run as done. The label comes from the [shared rule](evaluation.md#one-calculation-one-adjustment-policy-and-one-label); never relabel a job by hand. Detailed audit reports are on request, not a routine step.

## Showing the cards

The cards are one page, `RUN/cards.html`, and the user marks each card Interested or Pass. Show it the first way that works here:

- **The chat can draw HTML or publish a page** (Claude apps): show the page there. Its choices can be saved in the page, and **Download my choices** always works.
- **The AI tool runs on the user's own computer** (Claude Code, Codex CLI or Gemini CLI in a terminal): run `python3 tools/tracker.py serve --run RUN` and give the address it prints. That page adds an **Update queue** button that does the whole [update queue](#update-queue-archive-only) step's file work.
- **A cloud session** (Claude Code on the web, Codex cloud, any remote container): send `cards.html` as a file. The user opens it in a browser, marks the cards and sends back the **Download my choices** file. Do not give a `127.0.0.1` address: it would point at the cloud machine.

Before ending the session, tell the user that the run folder lives only in this session until they send their choices and say "update queue".

## Selection and handoff

The user may mark Interested or Pass and leave the rest unmarked. **Download my choices** is the common handoff in every AI tool; the page's own storage is an optional convenience. Do not claim to have received choices until the file has been imported. The choices file names each card's company, title, label and fit, but it holds no evaluations or postings: those live in the run folder.

Run `pipeline.py decide RUN/run.json CHOICES.json`, confirm the imported counts, then `pipeline.py export RUN/run.json --artifacts RUN/artifacts -o RUN/application_queue.json`. Choice files identify the run, source revision and job set. Export keeps interest separate from application status and includes the original posting text. `choices_imported: false` in a queue means no choices were imported; it is not the user's selection.

**Acting on a choices file in a later session:** first find its run folder. Match `run_id` and `source_commit` against `job-search/runs/`, or ask the user for the folder or the exported queue. If neither can be found, say so and offer to fetch and evaluate every Interested job by its ID. Never rank, choose or recommend from a subset of the picks, and always say how many of them were actually evaluated. Test material (`job-search/tests/`) is never a source of job evaluations or career evidence.

<a id="saving-a-run-archive-only"></a>

## Update queue (archive-only)

"Update queue" is one step that ends a search: the user's choices go in, the run is saved and their Interested jobs join the [tracker](../tracker/README.md) queue. "Save the run" means the same thing.

1. Get their **Download my choices** file. If it is not in this session, ask for it. Without it, nothing is saved: an unchosen run is not their selection. (The served cards page's **Update queue** button does steps 1 and 2 itself.)
2. Run `python3 tools/tracker.py update-queue RUN CHOICES.json`. It imports the choices (`pipeline.py decide`), exports `application_queue.json`, copies the run to `job-search/runs/<run-id>/` (leaving out the host-saved `searches/` and `details/` inputs, whose originals are under `raw/`), and adds each Interested job to the tracker. A job already in the tracker is linked, not duplicated; a dropped or applied job keeps its status. It refuses to overwrite a saved run.
3. If the user's copy uses Git, commit only the paths it prints: the run folder and the new files in `tracker/events/`. A cloud session can often push only its own branch: commit there, say it is not on the main branch yet and name the branch so the user can merge it.
4. Show the updated board ([queue shortcut](../tracker/README.md#working-the-queue-in-a-conversation)) and give the choice counts.

## Search footer

End every search reply that finishes a turn with this footer, following the footer rules and casing in [AGENTS.md](../AGENTS.md#application-workflow-stages-and-extras).

```
---

**Search:** 2026-11-20-a · 10 cards ready (6 Promising, 4 Stretch)  
**Next:** update queue (after Download my choices) · show my queue  
**Also:** more cards · status  
**Session:** Application (read-only) · Git 9f8b150  
Or reply in your own words.
```

- **Search:** run ID and card progress; while the run is still working, the status line ("6 of 10 cards ready · 9 of 15 fetched postings evaluated").
- **Next:** before the cards are ready, continue; once they are, update queue and show my queue. After the queue is updated, show my queue and build résumé.
