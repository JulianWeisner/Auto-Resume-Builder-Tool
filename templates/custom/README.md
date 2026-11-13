# Custom templates

[Templates](../README.md)

**Optional, and empty until you make one.** The [default templates](../README.md) work for most applications. If you prefer the look of a résumé or cover letter you already have, your agent can study it and build a template of your own. Tool updates never change this folder.

## How to start

Put one to three example documents in `custom/examples/` (PDF, Word or a screenshot), then say to your agent:

> Read templates/custom/README.md and build me a custom template from my examples.

Examples can be your own past résumés or ones you admire. If an example is someone else's, it is used only for design: none of its text is ever copied into your record or documents.

## Instructions for the agent

Work as an [information update session](../../agents/information-update.md) limited to templates/custom/ and the "Documents" section of career/preferences.md. Follow the [interviewing rules](../../AGENTS.md#interviewing-the-user): one short question at a time.

### 1. Read each example

Extract its text and render each page as an image to inspect it. Record the **design criteria**:

- Page: size, margins, number of pages, columns.
- Type: font families (or the closest common equivalent), sizes and weights for name, section headings, employer, role, body and contact line; line spacing; color.
- Rules and spacing: lines under headings, space before and after each level, indents, bullet character and indent.
- Dates: position (right-aligned, inline, own line), format (Mar 2021, 03/2021, 2021) and dash.

And the **information hierarchy**:

- Section order (for example summary, experience, skills, education) and section names.
- Within an entry: which comes first and which is most prominent, the employer or the role title; where location and dates sit.
- Whether there is a summary or positioning statement, and how long.
- Bullet density: bullets per role, typical bullet length.
- Where skills, certifications, links and any extras appear.

### 2. Check it against screening software

Compare the design with the "Screening-software safety" rules in the [default style guide](../resume/style-guide.md#implementation-and-delivery). Flag anything that commonly breaks text extraction: multiple columns, sidebars, tables used for layout, text boxes, icons or images carrying text, contact details in a page header or footer, unusual section names. Keep the look where it is safe; propose a safe equivalent where it is not (for example a single column with the same type scale instead of a sidebar).

### 3. Show the user what you found

Give a short summary of the design criteria and hierarchy, the screening-software risks and the safe equivalent you propose. When examples disagree, ask which one to follow, one question at a time. Ask before you change anything the user may have chosen on purpose.

### 4. Build the template

Create `custom/<template-name>/` with the same files as the default:

- `resume.html` (or `cover-letter.html`): flowing HTML with bracketed placeholders, semantic headings (h1 name, h2 sections, h3 employers, h4 roles) and print CSS for the page size and margins. No example text.
- `style-guide.md`: a copy of the [default style guide](../resume/style-guide.md) with its "Page and typography", "Alignment and spacing" and "Structure and punctuation" sections rewritten to match the new design. Keep the pagination, delivery, screening-software and verification rules.
- `resume.pdf` and `preview.png`, rendered from the HTML with placeholder text.

### 5. Test it

Fill a copy of the HTML with the user's own name and contact details and some placeholder bullets, render it to PDF, and run `python3 tools/resume_check.py <pdf> --source <html>`. Fix every FAIL. Show the user the preview.

### 6. Make it the default (if the user agrees)

Add the template's path to the "Documents" section of [career/preferences.md](../../career/preferences.md#documents). Delete nothing from the default templates.
