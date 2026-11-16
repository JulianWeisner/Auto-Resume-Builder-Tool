# Résumé layout reference

[Résumé style guide](style-guide.md) · Typography, spacing, implementation and the manual verification checklist for the [default résumé template](README.md). The template's HTML and CSS already apply these values, and `tools/build_resume.py` checks the rendered result, so agents filling in the template do not need this page. Read it when changing the template, building a [custom template](../custom/README.md), producing Word or another format, or when the automatic build cannot run.

## Page and typography

- US Letter portrait (or A4 where the user's market expects it); 0.75-inch margins on all sides. Full heading width on Letter: 7 inches (504 pt).
- Arial throughout; black text. Do not shrink type to force a page count. Where Arial is not installed (for example in cloud containers), Chromium substitutes the metric-compatible Liberation Sans; this is an accepted fallback, and the reference was rendered that way.
- Title / full name: 22 pt bold.
- Heading 1 / Experience, Education, Skills: 13 pt bold.
- Heading 2 / employer, consulting practice or optional short-form subgroup: 11.5 pt bold, ALL CAPS, 0.04 em letter-spacing. Its dates follow the label styling and are also in caps.
- Heading 3 / role title, client company plus title, earlier role: 10.5 pt bold, mixed case.
- Every date matches its associated identifying label's font family, size, weight and italic styling. Employer dates match employer headings; role and client dates match role headings; short-form dates match the bold identifying label; education dates match the bold institution. Keep heading dates at the right margin.
- Body and bullets: 10.5 pt, 13 pt leading. Company or practice context: same size and leading, italic. Contact line: 10 pt, 13 pt leading.
- Institution names and graduation dates are bold inline text, not headings. Keep the institution's colon bold and the degree or qualification regular.

## Alignment and spacing

- Section headings and Heading 2 start at the left margin. Heading 3 is indented 14 pt, aligned with body text. Right-aligned dates reach the right margin on every level.
- Below Experience, Education and Skills, body paragraphs are inset 14 pt on both sides. This includes company context, short-form entries, education and skills.
- Bullets sit 14 pt inside the left margin; bullet text starts 26 pt inside it. Continuation lines align with bullet text. Right inset is 14 pt.
- Name, contact line and positioning statement use the full width, without the body inset.
- Section headings: 10 pt before; 4 pt from the text bottom to the rule; 6 pt after the rule. The gap below every section rule is the same.
- Main section rules: 0.5 pt gray (#999999), full heading width. Chromium may draw sub-pixel rules at 0.75 pt; an accepted tolerance. No rules on employer or role headings, no shaded blocks, no decorative page-edge bars.
- Body and bullet space after: usually 4 pt. Context paragraphs: 7 pt. Separation between employers: 7 pt extra.
- Heading 2 rows: 10 pt before, except directly below a section rule, where the 6 pt rule gap applies. Heading 3 rows: 6 pt before. Heading rows: 4–5 pt after.

## Implementation and delivery

- HTML uses semantic heading levels: h1 is the name; h2 is Heading 1, h3 is Heading 2, h4 is Heading 3.
- For Word output, use native paragraph styles (Title, Heading 1–3, body) and lists, and right-aligned tab stops for dates, not spaces or layout tables. Set fonts, colors and tabs explicitly and remove inherited theme borders.
- **Screening-software safety:** no photos, icons, sidebars, multi-column layouts, layout tables or text boxes. Contact information stays in the body, not a page header or footer. Text must be selectable.
- Long headings wrap in the left area without colliding with dates. Allow extra row height; never shrink type or abbreviate a title silently.
- Use one page if the relevant evidence fits; two when necessary. The reference is a one-page placeholder, not a content budget.
- Use flowing paragraphs, never fixed coordinates copied from the preview.
- Print or render US Letter at 100% scale with browser headers and footers off.
- Render every finished document, inspect every page, check reading order, clipping, headings and dates, and remove every placeholder. Then build it with `tools/build_resume.py`, which renders, measures and checks it ([Stage 2](../../agents/stage-2-resume.md#build-and-check-before-delivery)).
- Save application documents outside templates/ and outside the career record.

## Formatting verification checklist

- Each short-form employer, role or engagement is its own paragraph, with its identifying label, dates and colon bold and the description regular.
- Education institutions and graduation dates are bold; qualifications are regular.
- Every date matches its label's font styling.
- Long entries wrap inside their insets; headings and dates do not collide. With caps letter-spacing, right-aligned dates end at the margin, not beyond it.
- Dated lists run newest first.
- The gap below every section rule matches (6 pt); the signature rule gap is 3 pt.
- Every rendered page passes the pagination rules; page one shows the strongest relevant evidence.
- Extracted text follows reading order. `tools/build_resume.py` automates this, the other text-level checks, the page count, stranded headings and near-empty last pages; see [Stage 2](../../agents/stage-2-resume.md#build-and-check-before-delivery).
