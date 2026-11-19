---
name: queue
description: Show the user's job queue board (Applied and Queued counts, queued jobs best fit first, with Build résumé and Drop). Use when they say "show my queue", "what's next" or run the queue shortcut.
---

# Show the queue

Follow [the tracker routine](../../../tracker/README.md#working-the-queue-in-a-conversation). Pick the first way that works here:

1. **This chat can draw HTML** (for example Claude's visual widgets): run `python3 tools/tracker.py board --fragment` and draw its output unchanged. Its buttons send "Build a résumé for …" and "Drop … from the queue" back into the chat.
2. **This AI tool runs on the user's own computer** (Claude Code, Codex CLI or Gemini CLI in a terminal): start `python3 tools/tracker.py serve` in the background and give the address it prints (usually `http://127.0.0.1:8765/`; it moves to the next free port when that one is busy). On that page Drop saves directly and Build résumé copies the request to paste back here.
3. **A cloud session** (Claude Code on the web, Codex cloud or any remote container): the address in step 2 would point at the cloud machine, not the user's computer, so do not give it. Run `python3 tools/tracker.py board`, which writes `tracker/board.html`, and send that file for the user to open in their browser. Its buttons copy the request to paste back here.

Do not retype, summarize or re-rank the jobs. The board is the answer; add at most one line.

Read-only: showing the queue writes nothing. Files the served page saved (Drop) still need committing: see the drop shortcut.
