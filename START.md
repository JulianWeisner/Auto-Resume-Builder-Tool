# Start here

This repository holds your career record and the rules an AI agent follows to turn it into job applications. You use it by talking to your AI assistant in this folder: every step below is something you say in the conversation, and the results appear there. You do not need to read anything else to use it.

## What you need

- Your own **private** copy of this repository on your computer ([how](README.md#get-your-own-private-copy)).
- An AI coding agent that can read and edit files in that folder: Claude Code, ChatGPT Codex, Gemini CLI or similar.
- Python 3. One setup command installs everything else ([below](#set-up-your-computer-or-ai-tool-once)).
- Your CV, and if you have them, recent résumés and cover letters.

## Set up your computer or AI tool (once)

The résumé PDF is built and checked by a script. In the repository folder, run:

```bash
python3 tools/build_resume.py --setup
```

It installs everything into a private folder in your user cache (no Homebrew or Node needed) and reuses it afterwards. To confirm a machine is ready, run `python3 tools/build_resume.py --check-setup`: it builds a small test résumé and says READY only if that works. Your agent can run both for you.

In a cloud tool such as Codex cloud, put the setup command in the environment's setup script, so every session begins ready. If the PDF still cannot be built, the agent says "Résumé drafted; PDF not built" with the reason and the fix, and never calls that résumé checked.

Want to see what a filled record looks like first? [examples/sample-person/](examples/sample-person/README.md) is a complete, made-up career.

## Step 1: fill your career record (once, then keep adding)

Open your agent in the repository folder and say:

> Read AGENTS.md. Help me fill my career record. Here is my CV.

The agent will:

1. **Import your CV** into records, keeping its wording as a starting point.
2. **Ask you to tell your story in order**, starting earlier than you think. A recruiter's advice: go chronologically, leave no stone unturned, you never know what will connect you to a role.
3. **Interview you one short question at a time,** with examples to react to (kinds of work, situations, systems, colleagues), because examples bring back memories. Skip anything you like.
4. **Record your goals and preferences**, including standard answers to job-portal questions.

Do it in one long session or several short ones. Everything you add makes every later application better, and you can always add more.

## Step 2 (optional): choose how your documents look

The default résumé and cover letter are clean, single-column layouts that screening software reads well ([see them](templates/README.md)). To use your own look instead, put one to three résumés you like in `templates/custom/examples/` and say:

> Read templates/custom/README.md and build me a custom template from my examples.

## Step 3 (optional): find jobs that fit your career

The agent can search for jobs, score each one against your whole record and show you review cards, best fit first. You mark each card Interested or Pass, and your Interested jobs become a queue you work through one résumé at a time.

1. **Connect HiringCafe** to your AI tool, once. It is free and needs no account: [how, for each AI tool](job-search/hiringcafe-setup.md). In Claude Code and Gemini CLI this folder already offers it; approve it when asked.
2. **Set up your search**, once. Say:

   > Set up my search.

   The agent asks one question at a time: where you search from and how far you will travel, which kinds of workplace you accept, the lowest pay you would consider, and the job titles you want. It saves the answers in `career/search-criteria.yaml`.
3. **Search.** Say **find me 10 jobs** (or any number). The agent searches, reads each full posting and scores it with the same rules as the verdict card below. You get review cards labelled Promising or Stretch; jobs that fail your conditions or fit poorly are counted but not shown.
4. **Choose.** Mark each card Interested or Pass, then say **update queue** (send the **Download my choices** file if the agent asks for it). Your Interested jobs join your queue.
5. **Work the queue.** Say **show my queue**. Each job has **Build résumé**, which starts Step 4 at the résumé, and **Drop**, for one you no longer want.

Where the cards and the queue appear depends on your AI tool: in a Claude app they are drawn in the conversation; in Claude Code, Codex or Gemini CLI on your computer they open as a page in your browser; in a cloud session the agent sends them as a file to open. Shortcuts: `/queue`, `/drop` and `/update-queue` in Claude Code and Gemini CLI, `$queue`, `$drop` and `$update-queue` in Codex.

## Step 4: apply for jobs in three replies

Start a new conversation with your agent in the repository folder:

> Read START.md and follow it.

Then:

1. **Paste the job posting.**
   You get a verdict card: a pass/fail check of the job's conditions (location, schedule, travel, work authorization) against your preferences, a fit estimate, a label (Promising, Stretch or Deprioritize), how many of the stated requirements you meet, the strengths and gaps behind it, and up to four questions that could change it. The fit estimate weighs every requirement in the posting against the evidence in your record; it is the agent's judgment, not a hiring prediction. A failed condition means Deprioritize, whatever the fit.
2. **Decide.** Reply with one of:
   - **build résumé**: go ahead with the résumé.
   - **full evaluation**: see the evidence and résumé plan first (below).
   - **pass on this job**: stop here; nothing more is built.
   - Or just answer the questions; the verdict updates.
3. **Get the résumé.** A tailored résumé and PDF, already checked for screening software. The agent fixes what fails before you see it, then gives you one line, for example "Checked: readable; 9 of 12 job terms covered; 3 have no evidence". Terms with no evidence are left out on purpose and noted for your cover letter or interview.

Nothing is built until you say **build résumé**, so a poor match costs no drafting time.

### When you want to see the evidence and plan

Reply **full evaluation** after the verdict card to see:

- **Asks and stories:** each thing the job asks for, your best matching story and how strong the match is, scored 0–4.
- **Storyboard:** the résumé outline the agent plans to write.
- **Review before build:** what to confirm before the résumé is built, such as title dates or recalled numbers.

If you say **build résumé** without asking for the full evaluation, the agent still does all of this work privately. You see less; the agent does not do less. You can ask for it at any point.

### Things you can say at any time

| Say | You get |
|---|---|
| **cover letter** or paste the portal's questions | A cover letter or answers that match the résumé |
| **reasoning report** | Why this résumé: each job requirement with your matching story, the choices made, titles and order, and the gaps to cover in a letter or interview |
| **proof report** | Whether it can be trusted: each résumé line with the records behind it, the facts confirmed, the screening check and how it was built. Ready in seconds |
| **handoff** | New facts from the conversation, packaged as proposed updates to your record. Nothing changes yet |
| **update my record** (with the handoff, or in your own words) | The agent applies the updates to your career record, in a separate conversation |
| **find me 10 jobs** / **more cards** | Review cards for new jobs that fit your career ([Step 3](#step-3-optional-find-jobs-that-fit-your-career)) |
| **update queue** / **show my queue** / **drop** *company* | Your chosen jobs join the queue; the queue board; a job taken off the queue |
| **I applied** | The submitted files are archived in applications/, and the [tracker](tracker/README.md) records the application |
| **[Company] replied** / **rejected**, or paste the employer's email | The reply is logged in the tracker; a pasted or forwarded email is saved unedited with the application |
| **show my applications** | Every application and where it stands: applied, acknowledged, in process, rejected and so on |
| anything in your own words | The agent works it out |

Every reply ends with a short footer: **Next** lists the main steps that fit that moment, **Also** the occasional ones, and **Session** says which kind of session you are in. You can also say **go**, **more detail** or **skip**.

### Two kinds of session

- **Application session** (the default): evaluates jobs and writes résumés, letters and answers. It reads your record and never changes it. Its only changes are archiving an application after you say **I applied**, logging the replies you report, saving a search when you say **update queue** and recording a **Drop**.
- **Information update session:** adds to or corrects your career record, including filling it the first time and applying a handoff. Start it by saying in words what it may change, for example "apply this handoff to my record".

## What never happens automatically

- No résumé is built before you say **build résumé**.
- No application is submitted and no employer is contacted.
- Nothing in your career record changes during an application, or ever unless you ask in words.
- No skill or job keyword is claimed without evidence in your record.
- Your data never leaves your copy of the repository. A search sends HiringCafe only job titles, a location and filters, never your record.

## More

- [How your career record is organized](schema/experience-schema.md)
- [AGENTS.md](AGENTS.md): the rules the agents follow
- [ROADMAP.md](ROADMAP.md): what is coming
