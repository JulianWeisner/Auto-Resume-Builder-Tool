---
name: update-queue
description: End a job search - import the user's card choices, save the run and add their Interested jobs to the queue. Use for "update queue", "save the run" or the update-queue shortcut.
---

# Update queue

Follow [Update queue](../../../agents/job-search.md#saving-a-run-archive-only) in the search runbook.

1. Find the finished run folder (it has `run.json` and `cards.html`) and the user's **Download my choices** file. If the choices file is missing, ask for it. On the user's own computer you can instead offer the served cards: `python3 tools/tracker.py serve --run RUN` opens the cards with an **Update queue** button that does step 2's work itself.
2. Run `python3 tools/tracker.py update-queue RUN CHOICES.json`.
3. If the user's copy uses Git, commit only the paths it prints: the run folder under `job-search/runs/` and the new files in `tracker/events/`. Push only as the user's habit and the session's branch rules allow.
4. Show the updated board (the queue shortcut) and give the choice counts.

"Update queue" authorizes only these writes ([AGENTS.md](../../../AGENTS.md#two-kinds-of-session)). It never overwrites a saved run.
