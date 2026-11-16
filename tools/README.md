# Scripts

Python 3 scripts that do the mechanical work: reading the whole record, checking it, quoting job postings exactly and checking finished résumés. Your agent runs them; you rarely need to. Each script prints its full usage when run with no arguments or `--help`.

## Setup (once)

Run `python3 tools/build_resume.py --setup` in the repository folder. It installs pinned versions of PyYAML, pypdf, pypdfium2, Playwright and Pillow, plus Chromium, into a private per-user folder (macOS `~/Library/Caches/resume-tool`, Linux `~/.cache/resume-tool`, Windows `%LOCALAPPDATA%\resume-tool`; `RESUME_TOOL_HOME` overrides it) and reuses it afterwards. Every script then restarts itself in that environment, so nothing else needs installing and your system Python stays untouched.

`python3 tools/build_resume.py --check-setup` builds a small test résumé and says READY only when it renders, reads back and passes the check.

Without setup, the scripts use what the machine already has: poppler or the Python PDF packages for reading, and Playwright (Python or Node) or an installed Chrome for rendering.

## The scripts

| Script | What it does | When |
|---|---|---|
| [build_resume.py](build_resume.py) | Renders the résumé HTML to PDF, measures the layout (page count, a heading stranded at a page bottom, a near-empty last page), runs the screening check, lists each problem with its fix and, on BUILD OK, saves a `<name>-snapshot/` folder of the decisions behind the résumé. `--setup` and `--check-setup` ready a machine | Every résumé |
| [resume_check.py](resume_check.py) | The screening-software check (text extraction, fonts, contact details, headings, dates, page count, reading order, first-person words) and job-term coverage. The build runs it for you | Inside every build |
| [proof_report.py](proof_report.py) | Writes `proof.html` from a build snapshot: each résumé line with the records behind it, term evidence, the check and the build log | When the user asks for a proof report |
| [current_view.py](current_view.py) | Prints every record's current, drafting-relevant fields plus your preferences, without historical metadata. Finds every collection under career/ automatically. `--search "words"`, `--index` and `--ids ID ... --related` help find stories | Before evaluating a job or drafting |
| [validate.py](validate.py) | Checks the record: YAML, unique IDs and anchors, unfinished placeholders, relationship backlinks, registered vocabulary tags, CV source lines, links. An empty skeleton passes | After every information update |
| [jd_key.py](jd_key.py) | Numbers a job posting, then copies the passages you tag into a verbatim key, rejecting anything that does not match word for word; assembles the fit check and computes the fit baseline from private scores (conditions as pass, fail or unknown) | When keying a job description |
| [agent_bundle.py](agent_bundle.py) | Prints AGENTS.md plus one task's modules as a single document (`d stage-1` for a report on one stage) | For chat tools that cannot open files |
| [check_skeleton.py](check_skeleton.py) | Fails if career data appears in the public tool repository | Upstream only; your filled copy fails it by design |

## Tests

`python3 -B -m unittest discover -s tools -p 'test_*.py'` runs the regression tests. They work on a temporary copy of the made-up [sample person](../examples/sample-person/README.md), never your own record. Build tests skip themselves on machines without a renderer and PDF reader.

See [Stage 1](../agents/stage-1-evaluate.md#preparation-always) for how `jd_key.py` keys a posting and scores fit, and [Stage 2](../agents/stage-2-resume.md#build-and-check-before-delivery) for how `resume_check.py` uses that key.
