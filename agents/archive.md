# Archive application (extra A)

Part of the [agent guide](../AGENTS.md). **Load when:** the user says they submitted an application ("I applied"), or asks for A. **Also read:** [archive conventions](../applications/README.md).

## Archive-only mode — standing authorization

The user's explicit statement that they submitted an application (for example, "I applied") authorizes adding that application's archive under applications/. It does not authorize applying, editing career records, tool files or templates, or including unrelated changes. Selecting A without confirming submission may prepare a package but must not mark it submitted. Ask only if the role, actual application date or exact submitted files are unclear.

Follow [Archive application](#archive-application-extra-a) and [archive conventions](../applications/README.md). Write only the identified application folder. If the repository uses Git, commit only that folder (on the user's specified branch, otherwise the current one), inspect the pending diff first and never force-push or include unrelated changes. Push only if the user's copy has a remote and they push as a habit. Without write access, produce a portable package (a ZIP) for the user to add later rather than asking for broader permissions.

## Archive application (extra A)

Trigger: the user confirms they applied. Follow [applications/README.md](../applications/README.md) to preserve the exact submitted resume PDF, full JD/metadata, submitted cover letter/answers when applicable, and detailed report. Never regenerate submitted artifacts or assume the latest draft was submitted.

Use the actual application date in the user's timezone, not the drafting or archive date. Ask when unknown. Verify the company/role and submitted version; ask only if ambiguous. Prepare the package before writing. If essential files are unavailable, request them and label the archive incomplete; do not manufacture replacements. A newly compiled report must be labeled retrospective, separating observed history from unavailable data.

Check for an existing same-application archive before adding one. Repeated "I applied" is not a new submission. Preserve submitted files and append dated status notes/corrections instead of overwriting history. Return the archive link, inventory and completion status. No submission, employer contact or career-record edits are authorized by A.

## Logging replies

When the user reports a reply ("Example Co invited me to interview", "rejected", "no reply after three weeks"), add a dated line to that archive's updates.md. This is part of the archive-only authorization. These notes are what later analysis of applications and response rates is built on.
