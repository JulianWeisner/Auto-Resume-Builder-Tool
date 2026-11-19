# Archive application (extra A)

Part of the [agent guide](../AGENTS.md). **Load when:** the user says they submitted an application ("I applied"), or asks for A. **Also read:** [archive conventions](../applications/README.md), and the [tracker](../tracker/README.md) when logging a reply.

## Archive-only mode — standing authorization

The user's explicit statement that they submitted an application (for example, "I applied") authorizes adding that application's archive under applications/. It does not authorize applying, editing career records, tool files or templates, or including unrelated changes. Selecting A without confirming submission may prepare a package but must not mark it submitted. Ask only if the role, actual application date or exact submitted files are unclear.

Follow [Archive application](#archive-application-extra-a) and [archive conventions](../applications/README.md). Write only the identified application folder and the new files the tracker writes in `tracker/events/`. If the repository uses Git, commit only those (on the user's specified branch, otherwise the current one), inspect the pending diff first and never force-push or include unrelated changes. Push only if the user's copy has a remote and they push as a habit. Without write access, produce a portable package (a ZIP) for the user to add later rather than asking for broader permissions.

## Archive application (extra A)

Trigger: the user confirms they applied. Follow [applications/README.md](../applications/README.md) to preserve the exact submitted resume PDF, full JD/metadata, submitted cover letter/answers when applicable, the build snapshot, and any reasoning or proof report written. Never regenerate submitted artifacts or assume the latest draft was submitted.

Use the actual application date in the user's timezone, not the drafting or archive date. Ask when unknown. Verify the company/role and submitted version; ask only if ambiguous. Prepare the package before writing. If essential files are unavailable, request them and label the archive incomplete; do not manufacture replacements. A newly compiled report must be labeled retrospective, separating observed history from unavailable data.

Check for an existing same-application archive before adding one. Repeated "I applied" is not a new submission. Preserve submitted files and append dated status notes/corrections instead of overwriting history. Return the archive link, inventory and completion status. No submission, employer contact or career-record edits are authorized by A.

## Tracker

After writing the archive, run `python3 tools/tracker.py add-archive applications/FOLDER` so the [tracker](../tracker/README.md) records the application as applied. When the job was queued from a search, that job gets the applied event. Commit the new file it writes in `tracker/events/` with the archive.

## Logging replies

When the user reports or forwards a reply ("Example Co invited me to interview", "rejected", "no reply after three weeks"), log it in the tracker; this is part of the archive-only authorization and covers only that application's events and saved emails.

- **An email:** save it unedited to the application's `correspondence/` folder with `tracker.py save-email MESSAGES.json --log`, never retyped ([format and scope](../tracker/README.md#commands)). Read the email from a connected mail tool when one is available; otherwise use the text the user pastes, unedited.
- **A reply the user tells you about:** `tracker.py add-event "COMPANY · ROLE" TYPE YYYY-MM-DD --note "…"`, with the user's words as the note. `closed` only when the user says so.
- Add a dated line to that archive's `updates.md` as well, so the archive reads on its own.

These events are what later analysis of applications and response rates is built on. Run `tracker.py validate` before committing.
