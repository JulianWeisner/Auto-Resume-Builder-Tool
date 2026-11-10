# Screening-software check

Part of the [agent guide](../AGENTS.md). **Load when:** building or revising a résumé for a specific job. **Also read:** [claim wording](writing/claim-wording.md), [plain language](writing/plain-language.md) and the résumé [style guide](../templates/resume/style-guide.md).

Most employers run résumés through screening software (an applicant tracking system, ATS) before a person reads them. These systems first extract the PDF's text, then search it for the employer's terms. A résumé fails silently if its text cannot be extracted cleanly or if it describes real experience in words the employer did not use. This module covers both, without ever adding a term the record does not support.

The check mirrors common screening-software behavior. It cannot promise how a particular employer's system scores a résumé.

## 1. Key the job description

Where you can run Python, build a verbatim key of the posting with `tools/jd_key.py` (standard library only; run it with no arguments for full usage):

1. `python3 tools/jd_key.py number posting.txt` prints the posting with line numbers.
2. Write a map giving every responsibility, requirement and nice-to-have its own tag (Do-1, Want-1, Nice-1), with an optional shorthand after `=`; tag conditions (location, schedule, travel, work authorization) as `Cond-1`, up to three company-context sentences as `About`, and mark boilerplate `skip` with a reason. Then run `python3 tools/jd_key.py render posting.txt - --save tags.json > key.md <<'MAP'` … `MAP`.
3. The script copies the employer's exact words. It fails on phrases that do not match verbatim, duplicate tags, untagged text and shorthands that add or change words; fix the map and rerun. Never retype the key by hand when the script is available.

Agents that cannot run code type the key by hand, quoting every bullet verbatim.

## 2. Keyword coverage before drafting

- Check each important requirement against the career records. Distinguish not examined, examined but not established, partially supported, and supported but not yet used. Do not infer missing experience from unexamined evidence.
- Identify relevant, evidence-backed tools and methods, then plan where each appears naturally in a bullet. Do not infer that a tool was used on a project from a general tools list.
- Keep a concise Skills section when relevant qualifications would otherwise disappear. Do not remove it only to meet a page target.
- This is a coverage check, not a reason to force every keyword in.

## 3. Automatic check before delivery

Run after rendering the PDF and before showing it to the user. Keep its files with the other application outputs, outside the career record.

1. **Write `terms.txt`** from the key: the words a screener would search for (role nouns, skills, domains, tools), usually 8–15, from the Do, Want and Nice tags. One line per term:

   ```
   Want-2 | stakeholder management / stakeholder alignment
   Do-4 | SQL
   Nice-1 | Kubernetes | unsupported
   ```

   The first term is the employer's own wording and must appear in that tag's quote. Alternatives after a slash count as covering it, but only if they mean the same or something narrower, never broader: "Claude" does not cover "Claude Code", and the check refuses an alternative that only drops words from the term. Mark a term `| unsupported` only after checking the records hold no evidence for it.

2. **Run** `python3 tools/resume_check.py resume.pdf --source resume.html --tags tags.json --terms terms.txt --json check.json`. Part 1 checks the PDF is readable by screening software:
   - text extracts with no unreadable glyphs, and all fonts are embedded
   - name, email and phone from career/contact.json appear as text
   - Experience and Education headings stand on their own lines
   - every date range uses one pattern and one dash
   - the page count is within `--max-pages` (default 2)
   - the extracted text keeps the source HTML's reading order
   - no first-person words (I, me, my, mine, myself)

   Part 2 checks every job term is covered or marked unsupported, and flags terms split by a line-wrap hyphen ("go-tomarket").

3. **Fix every FAIL and rerun** until PASS. Readability failures are layout or text fixes. A first-person word is rewritten with the user as the understood subject. A missing term is either reworded into a bullet the records already support or, after checking, marked unsupported. **Never add a term without evidence to pass the check.** Judge each WARN and note the decision in the private report.

4. **Deliver** the PDF with the check's one-line summary, for example "Checked: readable; 9 of 12 job terms covered; 3 have no evidence". Put the full output in the private report and list unsupported terms there: they are material for the cover letter or interview, not for the résumé.

Agents that cannot run code apply the [formatting verification checklist](../templates/resume/style-guide.md#formatting-verification-checklist) by hand and tell the user the automatic check did not run.
