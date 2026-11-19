# Job search toolkit

One Python pipeline, usable from any AI tool. Start with [the runbook](../agents/job-search.md); [scoring](scoring.md) is the shared evaluation specification. Job postings come from HiringCafe, connected once to the AI tool ([setup](hiringcafe-setup.md)); search criteria live in `career/search-criteria.yaml` and the capability profile in `career/capability-profile.yaml`. The tools do not call job providers, evaluate prose or submit applications. The host supplies provider responses and evaluation judgments.

## Setup

Python 3 and PyYAML are sufficient for search. `python3 tools/build_resume.py --setup` installs them with the résumé tools; for search alone:

```sh
python3 -m venv /tmp/job-search-env
/tmp/job-search-env/bin/python -m pip install -r job-search/requirements.txt
```

Use that environment's Python in the commands below. Runs belong outside the repository (for example `output/search/<run-id>/`, which Git ignores) until the user says "update queue". Connector-only environments can copy the toolkit and relevant career records from one pinned revision, preserving paths, including the shared `tools/evaluation.py` dependency. Clearly identify a snapshot versus a Git checkout.

## Accepted provider input

All existing inputs remain supported:

- Claude-style JSONL transcripts: `hiringcafe.py searches TRANSCRIPT RUN` and `extract TRANSCRIPT RUN`.
- Saved Markdown search listings and full descriptions.
- Saved MCP response JSON with `structuredContent.jobs` / `structuredContent.job`, direct `jobs` / `job` objects, direct structured detail objects, and text-content envelopes containing supported Markdown or JSON.

For searches without a transcript, use one file per plan ID, with `:` written as `__`. Prefer an envelope that retains the actual tool arguments:

```json
{
  "plan_id": "hardware-product:remote",
  "request": {"prompt": "The exact criteria sent to this connector", "limit": 10},
  "response": {"content": [], "structuredContent": {"count": 0, "jobs": []}}
}
```

The response is copied before interpretation. Parsed items and reported returned count must agree; `total_matches` is not the returned count. Unknown formats, missing IDs/titles/companies, unreadable dates and malformed pages become unresolved intake, not empty searches. Successful responses survive beside errors. Originals are content-hashed under `raw/searches/` and `raw/hiringcafe/`. Keep input `searches/` and `details/` separate from these generated archives.

Readers translate formats into common fields; they do not remove old formats. Add readers and fixtures as new connections are encountered. Do not generate a replacement provider response from memory. Original sources and unresolved errors must remain recoverable if an adapter changes.

Search receipts contain requested/returned filters when exposed. Each comparison is confirmed, changed or unknown. Provider query expansion, location aliases and freshness semantics can differ from the plan; inspect material differences. A call returning successfully is not proof that every filter was applied. The returned full-results URL is evidence of the provider's interpretation, not an independent guarantee of backend filtering.

## Commands and files

```sh
python3 job-search/tools/pipeline.py plan --target CARDS -o RUN/plan.json   # CARDS = review cards wanted
# Host calls HiringCafe; saves original responses under RUN/searches/.
python3 job-search/tools/hiringcafe.py searches RUN/searches RUN
python3 job-search/tools/pipeline.py candidates RUN --run-date YYYY-MM-DD
# Host fetches selected IDs; saves originals under RUN/details/.
python3 job-search/tools/hiringcafe.py ingest-raw RUN/details RUN
python3 job-search/tools/pipeline.py freeze RUN/jobs.json --run-id ID --run-date YYYY-MM-DD --commit FULL_SHA -o RUN/manifest.json
# For each fetched job (about five at a time), write a judgment draft, then:
python3 job-search/tools/pipeline.py result DRAFT.json --run-dir RUN
# When every fetched job has a result: fetch the next batch, or stop (cards reached, pool exhausted, 3x cap).
python3 job-search/tools/pipeline.py top-up RUN
# After fetching and ingesting a top-up batch:
python3 job-search/tools/pipeline.py freeze RUN/jobs.json --run-id ID --run-date YYYY-MM-DD --commit FULL_SHA --add -o RUN/manifest.json
python3 job-search/tools/pipeline.py assemble RUN -o RUN/run.json
python3 job-search/tools/pipeline.py validate RUN/run.json --artifacts RUN/artifacts
python3 job-search/tools/pipeline.py cards RUN/run.json -o RUN/cards.html
```

`plan` records criteria and requested filters. `search_log.json` retains every parsed occurrence and unresolved response. `candidates.json` records deterministic selection, reasons and input hashes. `jobs.json` contains deduplicated fetched jobs and intake errors. `manifest.json` freezes full posting-input hashes, source revision, run date and L1 rules. `results/` holds accepted per-job evaluations; `run.json` assembles them.

Runs use schema 1.3 only (earlier versions and their fit formulas were removed; Git history keeps them). Current CLI runs use `workflow_version: 2`. Each result carries a recomputed L1 receipt. New manifests also pin `evaluation_policy: shared-2`: the same rubric, credit (score / 4), weights, fit engine, documented ±5-point adjustment and Promising / Stretch / Deprioritize label as Stage 1. Each result records `label`, `requirements_met` and `stale_posting` (older than `stale_after_days`). The cards show Promising, then Stretch; Deprioritize jobs appear only as counts. A knocked-out job keeps its fit when every ask was rated. Result creation automatically applies age, completeness, location and pay gates; unknown conditions cannot become eligible. Location, workplace and travel use the shared checker `tools/conditions.py` with the `conditions` block of `career/search-criteria.yaml` (`radius_miles` from your `center`; remote outside the US is unknown); Stage 1 runs the same checker. Manifests frozen with the older place-list rules (`metro_places`, from the upstream project) keep that matcher so they revalidate unchanged. A Cond requirement the agent marks `fail` from a source-verified posting quote excludes the job. Status checks recompute L1 and detect changed intake or stale candidate selection. Historical runs remain readable and report that L1 rules were not pinned.

`pipeline.py status RUN` decides complete, partial or failed, and reports card progress (cards ready, postings evaluated, postings fetched). A run that names a card target is complete when the cards are reached, the search results are exhausted or the fetch cap (3× the cards) is reached. Older runs whose plan has `target_unique_jobs` keep the earlier rule: the target counts fetched jobs, and fewer leaves the run partial. A run that ends short because the results ran out does not prove the wider market has no jobs. `screen` remains an optional standalone inspection command. Do not overwrite a manifest (`freeze --add` only appends a top-up batch) or silently replace selected candidates.

## Cards and portable choices

Open `cards.html` directly in a browser, or serve it on localhost. It works without a host API. Local choices are scoped to the run and job set; browser storage is not automatically visible to either agent. Claude artifact storage remains optional, with capabilities:

```json
{"db":{"rules":[{"path":"decisions","read":"view","write":"admin"}]},"user":{},"downloads":true}
```

Use **Download my choices**, then:

```sh
python3 job-search/tools/pipeline.py decide RUN/run.json CHOICES.json
python3 job-search/tools/pipeline.py export RUN/run.json --artifacts RUN/artifacts -o RUN/application_queue.json
```

The import confirms the run ID and decision counts. New files also carry `source_commit` and `selection_key`; mismatches are rejected before updating any decisions. Earlier envelope files and bare maps remain supported with their available checks. The queue contains Interested jobs and original descriptions; `decision` and `application_status` are separate.

<a id="jd-ingestion-b5"></a>

## Validation and reference

```sh
python3 -B -m unittest discover -s job-search/tests
ARB_CAREER_REPO=examples/sample-person python3 job-search/tools/pipeline.py validate job-search/tests/fixtures/sample_run.json
python3 tools/validate.py
```

The tests never read your own record: record IDs and the capability profile come from the made-up [sample person](../examples/sample-person/README.md), and conditions from a made-up New York searcher (`tests/fixtures/criteria-nyc.yaml`). `ARB_CAREER_REPO` points every tool at another career folder, which is also how to try a search on the sample person.

Tests cover supported formats, unknown/count-mismatched responses, candidate eligibility/deduplication, completion, enforced L1, source artifacts and portable choices. Structural validation checks arithmetic and provenance, not whether an agent captured every qualification or interpreted evidence correctly.

- [JD ingestion](jd-ingestion.md): insert-only normalization, truncation, source quotes, tags and Greenhouse fallback.
- [Scoring](scoring.md): mandatory versus inferred asks, evidence rubric, knockout routing and fit.
- [Regression set](tests/regression/README.md): five public postings that broke earlier runs, checked through intake and L1.
- [Run schema](schemas/search-run.schema.json), [JD artifact schema](schemas/jd-artifact.schema.json), [application queue schema](schemas/application-queue.schema.json).
- [Saved runs](runs/README.md): archive-only authorization.

Detailed reports are useful during calibration and available on request. Routine delivery is the review cards, count summary and material limitations. Source retention supports resuming and investigating a problem without requiring the user to audit every run.

## Shared evaluation drafts

Before L2/L3 evaluation, render the complete map with `jd_ingest.py render ARTIFACT_DIR MAP --save tags.json`. Every substantive line must be selected or skipped with a reason. Merge repeated asks into one requirement using all their `source_tags`. Each requirement carries `quote_status: source_verified` and its primary `source` reference (tag, offsets and quote hash). Set `coverage.map_sha256` to the rendered artifact's selection-map hash. Full evaluations must account for every selected tag; `coverage.deferred` may map remaining tags to reasons only when L2 stopped the job without a fit score.

Optional draft fields `adjustment` and `adjustment_reason` use the same shared engine as Stage 1. Result creation stores `evaluation_policy`, `baseline_fit`, `adjustment`, `adjustment_reason` and the final `functional_fit`/`fit_percent`. Baseline and adjustment are separate on the cards. They cannot change L1 or knockout routing. Older saved runs and fixtures remain under their original formulas; do not automatically relabel or rescore them. See [the shared standard](../agents/evaluation.md).
