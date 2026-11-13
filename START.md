# Start here

This repository holds your career record and the rules an AI agent follows to turn it into job applications. You do not need to read anything else to use it.

## What you need

- Your own **private** copy of this repository on your computer ([how](README.md#get-your-own-private-copy)).
- An AI coding agent that can read and edit files in that folder: Claude Code, ChatGPT Codex, Gemini CLI or similar.
- Python 3, PyYAML and poppler for the checking scripts ([setup](tools/README.md#setup-once)). Without them the agent works by hand and tells you which checks did not run.
- Your CV, and if you have them, recent résumés and cover letters.

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

## Step 3: apply for jobs in three replies

Start a new conversation with your agent in the repository folder:

> Read START.md and follow it.

Then:

1. **Paste the job posting.**
   You get a verdict card: a fit estimate, a recommendation (Pursue, Stretch or Deprioritize), the strengths and gaps behind it, and up to four questions that could change it. The fit estimate weighs every requirement in the posting against the evidence in your record; it is the agent's judgment, not a hiring prediction.
2. **Decide.** Reply with one of:
   - **build résumé**: go ahead with the résumé.
   - **full evaluation**: see the agent's reasoning first (below).
   - **pass on this job**: stop here; nothing more is built.
   - Or just answer the questions; the verdict updates.
3. **Get the résumé.** A tailored résumé and PDF, already checked for screening software. The agent fixes what fails before you see it, then gives you one line, for example "Checked: readable; 9 of 12 job terms covered; 3 have no evidence". Terms with no evidence are left out on purpose and noted for your cover letter or interview.

Nothing is built until you say **build résumé**, so a poor match costs no drafting time.

### When you want to see the reasoning

Reply **full evaluation** after the verdict card to see:

- **Asks and stories:** each thing the job asks for, your best matching story and how strong the match is, scored 0–4.
- **Storyboard:** the résumé outline the agent plans to write.
- **Review before build:** what to confirm before the résumé is built, such as title dates or recalled numbers.

If you say **build résumé** without asking for the full evaluation, the agent still does all of this work privately. You see less; the agent does not do less. You can ask for it at any point.

### Things you can say at any time

| Say | You get |
|---|---|
| **cover letter** or paste the portal's questions | A cover letter or answers that match the résumé |
| **agent report** | How the agent worked: evidence used, choices made, what it left out and why |
| **handoff** | New facts from the conversation, packaged as proposed updates to your record. Nothing changes yet |
| **update my record** (with the handoff, or in your own words) | The agent applies the updates to your career record, in a separate conversation |
| **I applied** | The submitted files are archived in applications/ |
| **[Company] replied** / **rejected** | The reply is logged in that application's archive |
| anything in your own words | The agent works it out |

Every reply ends with a short footer: **Next** lists the main steps that fit that moment, **Also** the occasional ones, and **Session** says which kind of session you are in.

### Two kinds of session

- **Application session** (the default): evaluates jobs and writes résumés, letters and answers. It reads your record and never changes it. Its only change is archiving an application after you say **I applied**.
- **Information update session:** adds to or corrects your career record, including filling it the first time and applying a handoff. Start it by saying in words what it may change, for example "apply this handoff to my record".

## What never happens automatically

- No résumé is built before you say **build résumé**.
- No application is submitted and no employer is contacted.
- Nothing in your career record changes during an application, or ever unless you ask in words.
- No skill or job keyword is claimed without evidence in your record.
- Your data never leaves your copy of the repository.

## More

- [How your career record is organized](schema/experience-schema.md)
- [AGENTS.md](AGENTS.md): the rules the agents follow
- [ROADMAP.md](ROADMAP.md): what is coming
