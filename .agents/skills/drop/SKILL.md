---
name: drop
description: Drop a queued job the user no longer wants to pursue, with their reason if they give one. Use for "drop <company>", the board's Drop button or the drop shortcut with "Company · Role [reason]".
---

# Drop a queued job

Arguments: the job as "Company · Role" (or text that matches one job) and an optional reason. Example: `drop Example Freight · Operations Manager posting too old`.

1. Run `python3 tools/tracker.py add-event "COMPANY · ROLE" dropped YYYY-MM-DD --note "REASON"`, with today's date in the user's time zone. Leave out `--note` when the user gave no reason; never invent one. If the text matches several jobs, show the list and ask which.
2. If the user's copy uses Git, commit only the one new file it wrote in `tracker/events/`, and any event files the served board saved after a Drop click (`git status tracker/events`). Push only as the user's habit and the session's branch rules allow, and say where it went.
3. Report the job and the new queue count in one line.

The user's Drop authorizes only this ([AGENTS.md](../../../AGENTS.md#two-kinds-of-session)). A dropped job stays dropped; a change of mind is a new event, not an edit.
