# Application tracker

The tracker follows every job from the moment you mark it Interested in a search, or say **I applied**, to the last reply. Each event is one small file in [events/](events/README.md); a job is the events that share its ID. Status, replies and, later, patterns in who replies all come from these events. The tool is [tools/tracker.py](../tools/tracker.py), and your agent runs it for you.

The tracker describes your job search, not your career. It is never career evidence, and agents do not read it when they evaluate jobs or draft résumés, letters or answers (the same rule as [applications/](../applications/README.md)).

This README is part of the tool. The events in `events/` are **yours**: they stay in your private copy, and tool updates never touch them. The [sample person](../examples/sample-person/tracker/events/) shows a small filled tracker.

Jobs you mark Interested in a [search](../agents/job-search.md) join your **queue**: a board with Applied and Queued counts and the queued jobs best fit first, each with **Build résumé** and **Drop**.

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

## The queue board

The board shows only what helps you choose the next application:

- **Applied** and **Queued** counts.
- **The queue, best fit first:** Promising before Stretch, then highest fit. The rank shows priority and how many jobs are left; fit and label stay on each row from the search.
- **Old postings** get a "posted N days ago" tag after `stale_after_days` in your search criteria (21 days by default), the same cutoff the search uses.
- **Expand a row** for the business, what you would own, location, workplace, pay and age, the top three asks and the main gap, all from the search's queue export, and a link to the posting.
- **Build résumé** and **Drop** on each job.

Replies, rejections and waiting time stay off the board; the tracker still records them for later analysis.

## Working the queue in a conversation

When you ask to see your queue ("show my queue", "what's next?"), the agent shows the board the first way that works in your AI tool:

1. **The chat can draw HTML** (Claude apps): `python3 tools/tracker.py board --fragment`, drawn unchanged. Its buttons send "Build a résumé for …" and "Drop … from the queue" into the chat.
2. **The AI tool runs on your own computer** (Claude Code, Codex CLI, Gemini CLI): `python3 tools/tracker.py serve` and the address it prints. See [the local board](#local-board-trackerpy-serve).
3. **A cloud session** (Claude Code on the web, Codex cloud): `python3 tools/tracker.py board` writes `tracker/board.html`, which the agent sends you to open in a browser. Its buttons copy the request for you to paste back. A `127.0.0.1` address from a cloud session would point at the cloud machine, so the agent never gives one there.

The agent never retypes, summarizes or re-ranks the jobs.

- **Drop:** your Drop, or "drop *company*" in your own words, authorizes only `python3 tools/tracker.py add-event "COMPANY · ROLE" dropped YYYY-MM-DD --note "REASON"` and committing the one new file it writes in `tracker/events/`. Your reason is used if you give one; none is invented.
- **Build résumé:** starts the normal application workflow in [AGENTS.md](../AGENTS.md) at Stage 2 for that job. The full posting is `posting.text` for its `job_id` in the run's `application_queue.json`. Nothing changes in the tracker until you say you applied; the archive step then turns the queued job into the application (`add-archive`).

## Local board: `tracker.py serve`

`python3 tools/tracker.py serve` opens the board at `http://127.0.0.1:8765/` in your browser, from any AI tool or none. On that page **Drop** (with an optional reason) saves its event straight into `tracker/events/`; **Build résumé** copies the request to paste into your AI tool, because building is the agent's work. `--run RUN` also serves that search's review cards at `/cards`, with an **Update queue** button that saves your choices into the run folder and runs `update-queue`.

The server runs on your computer only: it answers only requests addressed to `127.0.0.1` or `localhost`, refuses saves from other sites and anything that is not JSON, and writes files without committing them (commit them afterwards, or ask the agent to). If port 8765 is busy it uses the next free one and prints the address. `--no-open` skips opening the browser.

## Shortcuts in each AI tool

| Shortcut | Claude Code | Codex | Gemini CLI |
|---|---|---|---|
| Show the queue | `/queue` (`.claude/skills/queue/`) | `$queue` (`.agents/skills/queue/`) | `/queue` (`.gemini/commands/queue.toml`) |
| Drop a job: Company · Role [reason] | `/drop` | `$drop` | `/drop` |
| End a search | `/update-queue` | `$update-queue` | `/update-queue` |

Each shortcut only points at the routines in this README and the search runbook, and at `tools/tracker.py`; no rules live in them. The Claude Code and Codex skills are identical copies (a test checks), and the Gemini commands point to the `.agents/skills/` files. Plain words ("show my queue", "drop Example Freight") work the same without them.

## Logging applications and replies

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
python3 tools/tracker.py serve [--run RUN] [--port N] [--no-open]   # the board (and RUN's cards) on this computer
python3 tools/tracker.py update-queue RUN CHOICES.json   # end of a search: choices, save the run, queue
python3 tools/tracker.py import-queue job-search/runs/RUN/application_queue.json
```

`save-email` takes a JSON list of messages with `id`, `threadId`, `sender`, `toRecipients`, `date` (ISO 8601), `subject` and `plaintextBody` (`senderName` optional), the format the Gmail connector's `get_message` returns. Each message gets two added fields: `archive` (the application folder) and `kind` (the event type). An email from another mail service or pasted by you works the same way: the agent writes it in this format with the body unedited, and uses the service's message ID, or a made-up stable ID such as `pasted-2026-11-18-1`, as `id`. Each email is written once, with a short header and the unedited plain-text body; a message already saved in that folder is skipped.

`tracker/board.html` is generated on request and ignored by Git; it is a view, not data.

## Email scope

Only email about an archived application is saved. Not saved: account sign-ups, verification codes and sign-in links (they can give access to your accounts), job-alert newsletters, and email about applications you have not archived. An email that names no role and cannot be matched to one of several same-day applications is saved once, in the shared company folder, and logged on each candidate role with a note.
