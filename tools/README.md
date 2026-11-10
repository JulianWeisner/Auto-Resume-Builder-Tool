# Scripts

Python 3 scripts that do the mechanical work: reading the whole record, checking it, quoting job postings exactly and checking finished résumés. Your agent runs them; you rarely need to. Each script prints its full usage when run with no arguments or `--help`.

## Setup (once)

- Python 3.8 or later.
- `pip install pyyaml` for `current_view.py` and `validate.py`.
- poppler (`pdftotext`, `pdfinfo`, `pdffonts`) for `resume_check.py`: `brew install poppler` on macOS, `sudo apt install poppler-utils` on Debian or Ubuntu, or the poppler package for Windows.
- To render HTML templates to PDF: print from a browser (US Letter, 100%, headers and footers off), or any headless Chromium.

## The scripts

| Script | What it does | When |
|---|---|---|
| [current_view.py](current_view.py) | Prints every record's current, drafting-relevant fields plus your preferences, without historical metadata. Finds every collection under career/ automatically | Before evaluating a job or drafting |
| [validate.py](validate.py) | Checks the record: YAML, unique IDs and anchors, unfinished placeholders, relationship backlinks, registered vocabulary tags, CV source lines, links. An empty skeleton passes | After every information update |
| [jd_key.py](jd_key.py) | Numbers a job posting, then copies the passages you tag into a verbatim key, rejecting anything that does not match word for word; can assemble a report and compute a fit baseline from private scores | When keying a job description |
| [resume_check.py](resume_check.py) | Screening-software check of a rendered PDF (text extraction, fonts, contact details, headings, dates, page count, reading order, first-person words) and job-term coverage | Before delivering every résumé |
| [agent_bundle.py](agent_bundle.py) | Prints AGENTS.md plus one task's modules as a single document | For chat tools that cannot open files |
| [check_skeleton.py](check_skeleton.py) | Fails if career data appears in the public tool repository | Upstream only; your filled copy fails it by design |

See [agents/screening-check.md](../agents/screening-check.md) for how `jd_key.py` and `resume_check.py` work together.
