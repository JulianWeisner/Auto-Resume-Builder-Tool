# Auto-Resume-Builder-Tool

**This is not an app you install.** It is a folder of rules, templates and scripts that the AI assistant you already use reads and runs: Claude Code, ChatGPT Codex, Gemini CLI or any assistant that can read and edit files in a folder. You do not open this repository to use it. You talk to your assistant, and the assistant does the work in the conversation:

| You say to your assistant | You get, in the conversation |
|---|---|
| "Help me fill my career record. Here is my CV." | An interview, one question at a time, that turns your CV and your story into a structured career record |
| *Paste a job posting* | A verdict card: the job's conditions against your preferences, a fit estimate, a label, and the questions that could change it |
| "build résumé" | A tailored, checked résumé PDF that claims only what your record supports |
| "cover letter" or *paste the portal's questions* | A cover letter and answers in your own voice |
| "I applied" | An archive of the posting and the files you sent, recorded in your application tracker |
| *Paste an employer's reply*, or "show my applications" | The reply logged against that application; a list of where each application stands |

The assistant is the interface. The repository is where your career record lives and where the rules are written down, so every assistant follows the same rules and your data stays in your own private copy. Nothing is built until you say yes, and nothing goes to an employer without your approval.

Job search and an application queue are on the way ([roadmap](roadmap/2026-11-18-roadmap.md)). Their review cards and queue board also appear in the conversation where the assistant can draw them, and open as a page in your browser where it cannot.

**New here? Read [START.md](START.md).** It takes you from an empty copy to your first application.

## Why this product exists

### The problem: cold applications cost a lot and rarely pay off

Cold applications are applications with no referral and no personal contact. Most job applications are cold, and their response and interview rates are low: often in the single-digit percentages, or less. Three things drive this:

- **Ghost jobs:** roles that will never be filled. Some are posted by companies that will only hire internally. Others are posted to make a company look like it is growing.
- **Applicant tracking systems (ATS):** they filter applications heavily before a person reads them.
- **AI:** it has changed the market on both sides. Applicants send more applications, and employers filter them harder.

Each good application must be specific to the job. It needs a tailored résumé, a cover letter, and answers to the employer's questions. That costs time, energy and emotion. The cost per application is high, but the chance of a reply is low. **This imbalance is the problem.**

### The common responses

Job seekers usually respond in one of two ways, and both fail:

- **Send many generic applications.** The cost goes down, but the applications lose quality and personality, and screening filters them out. LinkedIn's Easy Apply works this way: you choose one of a few saved résumés and send it to many roles.
- **Send a few polished applications.** The quality goes up, but you produce too few applications, too slowly, to get replies.

A polished application is expensive for another reason. You must recall evidence that your CV and earlier résumés do not hold: your stories, numbers, context, and what you liked or did not like in your work. So each tailored application starts with remembering and rewriting from the beginning.

### The solution: less work, higher quality

This product decreases the time, energy and emotion that each application costs. It keeps what makes an application work: quality, your own personality, a human touch, and truth. Every claim comes from your own record.

You stay in control. The tool does not build an application until you say yes, and it never submits anything without your approval. No AI résumé slop: the tool builds résumés tailored to each job, at a low human cost.

## What the product is

The product has three layers.

### Layer 1: a career database

The database goes far beyond a CV. You talk to an AI agent, and the agent sorts your experiences, skills, results and preferences into a structured record. Both AI agents and code can read that record and extract from it.

### Layer 2: application tools

These tools use the database to do the work for each job:

- **Career informed search:** find jobs that match your career.
- **Job match analysis:** a fit score and a verdict card before any work starts.
- **Tailored résumé:** built from your record and checked so screening software can read it.
- **Cover letters and application answers:** in your own voice.
- **Interview preparation:** the stories most likely to come up, practiced from memory. It starts when an employer asks you for an interview.

### Layer 3: job search management

These tools work across many jobs over time:

- **Application tracking and insights:** an archive of each job description and the files you sent, the replies you received, and patterns in what works.
- **Application queue:** review postings quickly, and say yes or no to each. A yes queues the application.

### How the layers work together

The layers form a loop. During each application, agents ask you questions to improve your résumé, and those details go back into the database. As you apply, you log the replies you get, and the system shows which applications work. So the database, and each application built from it, improves with use.

All three layers rest on the same rules: claims trace to your record, your data stays in your own copy, and the tool works with any AI tool.

## Status

Early version. What is here today:

- ✅ **The career-record skeleton:** every page and folder the tool needs, empty, each saying what it is for and how it gets filled.
- ✅ **The record reference and templates:** how roles, experiences, outcomes, projects and skills are stored, with blank copyable records.
- ✅ **Agent rules for filling your record** from your CV and your story, one question at a time.
- ✅ **Résumé and cover-letter templates** with style guides, plus a guided way to build **your own template** from résumés you like.
- ✅ **Writing guides:** plain language (ASD-STE100-informed, with formulaic AI phrasing removed) and claim wording for strong, truthful bullets.
- ✅ **The guided application flow:** paste a posting, get a verdict card with a weighted fit estimate, then a full evaluation (asks-and-stories scoring, storyboard, review before build), a tailored résumé, cover letter and portal answers, a handoff of new facts and an archive of what you submitted.
- ✅ **One-command résumé build** that renders the PDF, measures its layout and runs the screening-software (ATS) check, with a one-command setup for any computer or AI tool, and a proof report that traces every résumé line back to your records.
- ✅ **Application tracker:** every application you archive is recorded, with the replies you report or paste (saved unedited) and a status worked out from those events, ready for later analysis.
- ✅ **A made-up sample person** ([examples/sample-person/](examples/sample-person/README.md)) showing what a filled record looks like.

What comes next is in [ROADMAP.md](ROADMAP.md).

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
git checkout upstream/main -- AGENTS.md START.md CLAUDE.md GEMINI.md schema career/_templates agents templates/README.md templates/resume templates/cover-letter tools tracker/README.md examples
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
| [agents/](agents/) | The agent's modules: the shared evaluation standard, Stage 1 evaluation, Stage 2 résumé and screening check, Stage 3 letters and answers, handoff, archive, information update, and the writing guides | Tool |
| [templates/](templates/README.md) | Default résumé and cover-letter templates and style guides | Tool |
| [templates/custom/](templates/custom/README.md) | Your own templates, built from examples you like | **Yours** |
| [source-material/](source-material/README.md) | Your CV snapshot, evidence journal and document extracts | **Yours** |
| [Curriculum-Vitae.md](Curriculum-Vitae.md) | Your working CV | **Yours** |
| [applications/](applications/README.md) | What you submitted, per application | **Yours** |
| [tracker/](tracker/README.md) | The application tracker's rules | Tool |
| [tracker/events/](tracker/events/README.md) | Your applications' events: applied, replies, interviews | **Yours** |
| [tools/](tools/README.md) | Scripts the agent runs (Python 3; [setup](tools/README.md#setup-once)) | Tool |
| [examples/](examples/sample-person/README.md) | A made-up sample career, also used by the tests | Tool |

## Contributing to the tool

Improvements to the tool are welcome. Pull requests to this repository must never contain anyone's career data: an automatic check fails any pull request that adds files or records to the data folders. Build and test changes in your own private copy, then copy only the tool files into your contribution.
