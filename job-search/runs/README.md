# Saved batch runs

Each saved batch screening run lives in its own folder, `job-search/runs/<run-id>/`, so later runs can be compared and screening patterns studied. Deprioritized jobs are kept here even though they are not shown in review.

**Empty until your first saved search; the folders here are yours.** A folder is added only when you say "update queue" or "save the run" (an archive-only action that also adds your Interested jobs to the [tracker](../../tracker/README.md); see `agents/job-search.md`). It holds:

- `run.json`: the validated run (schema 1.3), with your choices copied in by `pipeline.py decide`.
- `jobs.json`: the L1 input written by `hiringcafe.py extract`.
- `cards.html`: the rendered review page.
- `application_queue.json`: the handoff of Interested jobs (`pipeline.py export`).
- `artifacts/<artifact_id>/`: B5 JD artifacts (`jd.txt`, `artifact.json`).
- `raw/`: provider responses saved as received (`raw/hiringcafe/<job id>.md`, Greenhouse JSON).
- `screen.jsonl`: the `pipeline.py screen` output.

Run files are records of a screening run, not career evidence. Never edit a saved run in place; save a rescore or rerun as a new folder.
