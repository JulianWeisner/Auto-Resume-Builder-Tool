# Application tracker

The tracker follows every job you apply to, from the day you say **I applied** to the last reply. Each event is one small file in [events/](events/README.md); a job is the events that share its ID. Status, replies and, later, patterns in who replies all come from these events. The tool is [tools/tracker.py](../tools/tracker.py), and your agent runs it for you.

The tracker describes your job search, not your career. It is never career evidence, and agents do not read it when they evaluate jobs or draft résumés, letters or answers (the same rule as [applications/](../applications/README.md)).

This README is part of the tool. The events in `events/` are **yours**: they stay in your private copy, and tool updates never touch them. The [sample person](../examples/sample-person/tracker/events/) shows a small filled tracker.

**Coming with career informed search:** a queue of jobs you marked Interested, shown as a board in the conversation with **Build résumé** and **Drop** on each job. The tool already has the commands for it (`board`, `update-queue`, `import-queue`); until search arrives, the board shows only your Applied count.

## Rules

- **One permanent ID per job.** A job keeps its first ID for life. A job you applied to without a search is keyed by its archive folder name (`Company.Role.YYYY-MM-DD`). A job from a search will keep its posting ID, and applying adds the archive folder to it without renaming.
- **Status is derived, never stored.** The tool reads the dated events. A final event (offer, rejected, withdrawn, closed, dropped) wins; otherwise the furthest step reached (in process, acknowledged, applied, queued). History and status cannot disagree.
- **One file per event, never edited.** A file is named by its date, type and a hash of its content (`2026-11-18-rejected-1a2b3c4d5e6f.json`). Corrections are new events or notes; `validate` reports a file whose content no longer matches its name.
- **Why files, not one ledger:** two branches (or two devices) that add events add different files, so they merge cleanly everywhere, including GitHub's merge button. The same event added twice has the same name and content and collapses to one file.
- **Original first.** An email event points to the email saved unedited in the application's `correspondence/` folder, with its hash and message ID. The event interprets; the saved email is the evidence.
- **Applied needs an archive.** Only your confirmed submission, archived under [agents/archive.md](../agents/archive.md), creates an applied event.
- **Every archived application is in the tracker.** `validate` fails otherwise. If you archived applications before the tracker existed, ask your agent to add each one (`add-archive`).

## Event

One JSON object per file, keys sorted, on one line:

```json
{"archive":"applications/Example-Freight-Co.Operations-Manager.2026-11-10","company":"Example Freight Co.","date":"2026-11-10","file":"applications/Example-Freight-Co.Operations-Manager.2026-11-10/job-description.md","job":"Example-Freight-Co.Operations-Manager.2026-11-10","note":"Submission confirmed by the user; see the archive","posting_url":"https://example.com/jobs/operations-manager","role":"Operations Manager","source":"archive","type":"applied"}
```

Any event may also carry the job's details: `company`, `role`, `posting_id`, `posting_url`, `search_run` and `archive`. The first event of a job carries them; a later event sets only what changes. The latest event that sets a detail wins.

| Field | Meaning |
|---|---|
| `job` | The job's permanent ID |
| `posting_id` | The job board's ID for the posting, when known. Links a search to the archive |
| `search_run` | The search where you marked the job Interested, or null |
| `archive` | The application folder, or null while queued |
| `date` | YYYY-MM-DD in your time zone (the computer's, or `TRACKER_TZ`) |
| `type` | queued · applied · acknowledged · screen · assessment · interview · offer · rejected · withdrawn · closed · dropped · note |
| `source` | archive · email · search-run · user |
| `file`, `sha256` | The saved original behind the event. Required for email events |
| `gmail_message_id` | The email's message ID. Required for email events; one message is logged once per job |
| `note` | Anything the event alone does not say, such as a role the email did not name |

- `dropped`: you chose not to pursue a queued job, with your reason in the note when you give one. `withdrawn` is different: pulling out of an application already sent.
- `closed`: a job that went quiet past the company's stated reply window, or whose posting was removed. You decide it; the tool never closes a job on its own.
- `screen`, `assessment` and `interview` all count as "in process".

## Working with the tracker in a conversation

| You say | The agent |
|---|---|
| **I applied** | Archives the application ([agents/archive.md](../agents/archive.md)), then runs `add-archive`, which records it as applied |
| *Paste or forward an employer's email*, or "log the reply from *company*" | Saves the email unedited to that application's `correspondence/` folder and logs its event (acknowledged, screen, interview, rejected…) |
| "*Company* invited me to interview on *date*", "I withdrew from *company*", "close *company*" | Adds that event with `add-event`, using your words as the note |
| **show my applications** | Runs `status` and shows the result |

Each of these authorizes only the new event files (and, for an email, the saved email) for that one job. They never change your career record. Use your own words for notes; the agent does not invent a reason.

## Commands

```sh
python3 tools/tracker.py status [--all]          # text list by status, newest activity first
python3 tools/tracker.py validate                # schema, files, hashes, archive coverage
python3 tools/tracker.py add-archive applications/FOLDER
# add-event takes an exact ID or text matching one job's "company · role"
python3 tools/tracker.py add-event "Example Freight · Operations Manager" interview 2026-11-20 --note "Panel with the ops director"
python3 tools/tracker.py save-email MESSAGES.json --log
python3 tools/tracker.py board [--fragment]      # the board: tracker/board.html, or the body for a chat
```

`save-email` takes a JSON list of messages with `id`, `threadId`, `sender`, `toRecipients`, `date` (ISO 8601), `subject` and `plaintextBody` (`senderName` optional), the format the Gmail connector's `get_message` returns. Each message gets two added fields: `archive` (the application folder) and `kind` (the event type). An email from another mail service or pasted by you works the same way: the agent writes it in this format with the body unedited, and uses the service's message ID, or a made-up stable ID such as `pasted-2026-11-18-1`, as `id`. Each email is written once, with a short header and the unedited plain-text body; a message already saved in that folder is skipped.

`tracker/board.html` is generated on request and ignored by Git; it is a view, not data.

## Email scope

Only email about an archived application is saved. Not saved: account sign-ups, verification codes and sign-in links (they can give access to your accounts), job-alert newsletters, and email about applications you have not archived. An email that names no role and cannot be matched to one of several same-day applications is saved once, in the shared company folder, and logged on each candidate role with a note.
