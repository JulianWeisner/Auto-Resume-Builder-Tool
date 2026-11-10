# Auto-Resume-Builder-Tool

A free, personalizable system for turning your whole career into tailored job applications with the AI coding agent you already use: Claude Code, ChatGPT Codex, Gemini CLI or any tool that can read files in a folder.

You keep your career as a structured, truthful record. The agent reads it and, for each job, judges the fit, then writes a résumé, cover letter and portal answers that only claim what your record supports.

**New here? Read [START.md](START.md).**

## Status

Early version. What is here today:

- ✅ **The career-record skeleton:** every page and folder the tool needs, empty, each saying what it is for and how it gets filled.
- ✅ **The record reference and templates:** how roles, experiences, outcomes, projects and skills are stored, with blank copyable records.
- ✅ **Agent rules for filling your record** from your CV and your story.
- 🔜 **The application workflow:** fit check, résumé build, automatic screening-software check, cover letters and archive. See [ROADMAP.md](ROADMAP.md).

## Get your own private copy

Your copy will hold your contact details, work history and job applications, so **make it private and never fork this repository** (on GitHub, a fork of a public repository stays public).

**On GitHub:** click **Use this template** → **Create a new repository**, choose **Private**, then clone your new repository to your computer.

**Without GitHub, or on another host:**

```bash
git clone https://github.com/JulianWeisner/Auto-Resume-Builder-Tool.git my-career
cd my-career
git remote rename origin upstream      # keep a link for tool updates
# optional: create an empty PRIVATE repository on your host, then
git remote add origin <your-private-repo-url>
git push -u origin main
```

Working only on your computer, with no remote at all, is fine too.

## Getting tool updates

The tool improves over time. Updates only touch the tool's files, never your data, so pull those paths rather than merging the whole repository:

```bash
git remote add upstream https://github.com/JulianWeisner/Auto-Resume-Builder-Tool.git   # once, if not already set
git fetch upstream
git checkout upstream/main -- AGENTS.md START.md CLAUDE.md GEMINI.md schema career/_templates tools
git commit -m "Update tool from upstream"
```

[UPSTREAM.md](UPSTREAM.md) lists what changed in each update.

## What is in the repository

| Path | What it is | Yours or the tool's |
|---|---|---|
| [START.md](START.md) | How to use the tool | Tool |
| [AGENTS.md](AGENTS.md) | Rules every AI agent follows here (CLAUDE.md and GEMINI.md point to it) | Tool |
| [schema/](schema/experience-schema.md) | How the career record is organized | Tool |
| [career/](career/README.md) | Your career record: index, story, preferences, vocabulary, contact details and collections of records | **Yours** |
| [career/_templates/](career/_templates/README.md) | Blank, copyable records | Tool |
| [source-material/](source-material/README.md) | Your CV snapshot, evidence journal and document extracts | **Yours** |
| [Curriculum-Vitae.md](Curriculum-Vitae.md) | Your working CV | **Yours** |
| [applications/](applications/README.md) | What you submitted, per application | **Yours** |
| [tools/](tools/) | Scripts the agent runs (Python 3) | Tool |

## Contributing to the tool

Improvements to the tool are welcome. Pull requests to this repository must never contain anyone's career data: an automatic check fails any pull request that adds files or records to the data folders. Build and test changes in your own private copy, then copy only the tool files into your contribution.
