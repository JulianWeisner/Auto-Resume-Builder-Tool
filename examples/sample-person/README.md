# Sample person: Riley Example

**Fictional.** Riley Example, Northwind Logistics, Brightway Grocers and every detail here are made up. Nothing here is anyone's real career.

This folder shows what a filled career record looks like: compare it with the empty skeleton in [career/](../../career/README.md). The tool's tests also use it as their test data, so it stays valid: `python3 tools/validate.py` passes on it.

| Path | What it shows |
|---|---|
| [career/README.md](career/README.md) | A filled career index and record locator |
| [career/experience/records.md](career/experience/records.md) | A grouped collection: two jobs, each with experiences, limits and an outcome |
| [career/northwind/](career/northwind/roles.md) | An organization collection for one deep employer: a formal title, a functional-title progression with its date window, experiences and outcomes |
| [career/education/records.md](career/education/records.md) | A degree and a certificate |
| [career/vocabulary.md](career/vocabulary.md) | A small tag vocabulary |
| [career/preferences.md](career/preferences.md) | Conditions, motivation and portal answers |
| [postings/](postings/example-freight.txt) | A made-up job posting to try the workflow on |
| [applications/](applications/Example-Freight-Co.Operations-Manager.2026-11-10/job-description.md) and [tracker/events/](tracker/events/) | Riley's application to that posting: the archive's job description, the employer's acknowledgment saved unedited, and the tracker events (applied, acknowledged, screen) built from them |
| [source/](source/Riley-Example-CV.md) | Riley's made-up CV, with the usual problems, and [answers](source/interview-answers.md) for a simulated onboarding interview that correct them |

To try the tool on Riley without touching your own record, copy this folder's `career/` (and `applications/` and `tracker/` for the tracker) over the empty ones in a scratch copy of the repository.
