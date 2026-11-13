# Résumé style guide

[Templates](../README.md) · [Default résumé template](README.md)

This guide defines the default résumé's appearance: a single-column, screening-software-friendly layout. It defines appearance only, not career evidence or a fixed story count. The rendered [PDF](resume.pdf) is the visual reference; [preview.png](preview.png) shows the same page. If you made your own template ([custom templates](../custom/README.md)), its style guide replaces this one.

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

## Structure and punctuation

1. Full name, contact line and an optional concise positioning statement.
2. Experience:
   - Employer and overall dates; optional one-line context; selected role title and its dates.
   - Optional earlier-role rows under the same employer.
   - A consulting or freelance practice can appear as one employer with client engagements as role rows ("Client Company: Title"), rather than as many separate jobs. Use the role's `presentation_note` when the record has one.
   - Optional short-form subgroup for relevant older or secondary work.
3. Education: **Institution:** Degree or qualification | **Graduation year**.
4. Skills: Skill | Skill | Skill.
5. Optional personal signature (below).

Use colons to relate company to title and institution to qualification. Use vertical bars to separate list items and inline date fields. Short-form pattern: **Company: Title | Dates:** Brief description, with the whole identifying label, date and colon bold and the description regular. Each employer, role or engagement is its own paragraph.

Remove every unused optional block rather than leaving empty space or placeholders. Before removing Skills, run the [keyword-coverage audit in Stage 2](../../agents/stage-2-resume.md#requirement-coverage-and-selection): keep a concise section if relevant, evidence-backed qualifications would otherwise disappear. A page target alone is not a reason to remove it.

Order every dated list newest first: employers, roles within each employer, short-form entries, education and certifications. Use the end date; where end dates match, put the later start date first. Story priority affects the summary and bullet selection, never entry order. Skills may be ordered by relevance.

Choose one supported functional title from each either-or set. Do not combine alternatives, infer promotions, move work between periods or sum overlapping dates. Include supported completion years; leaving one out is a deliberate tailoring choice, not an invented date.

## Pagination

- Start with natural document flow. Do not insert a page break only to keep an entire employer or section together. Prefer breaks between roles or complete entries.
- Keep each heading with its context and first complete bullet or entry. Never strand a heading at a page bottom.
- Keep individual bullets together when they fit on one page. For paragraphs that must split, leave at least two lines on each page.
- Avoid a final page with only a few trailing lines.
- Fix an awkward one-word final line through careful wording only where meaning is preserved.
- Do not shrink text or silently remove evidence to solve pagination.
- Check what the recruiter sees on page one. Do not bury the strongest relevant evidence just to preserve employer grouping.
- Before forcing a manual break, compare natural flow with a break between roles, and record the choice in the private report, not the résumé.
- Verify these rules in the rendered output, page by page. CSS rules or successful text extraction alone do not prove it.

Implementation: in HTML, avoid breaks after headings and context and inside individual bullets, and let lists and sections flow. In Word, chain headings and context with Keep with next through the first bullet; do not chain every bullet. If a renderer strands a heading, group only the heading, context and first entry.

## Implementation and delivery

- HTML uses semantic heading levels: h1 is the name; h2 is Heading 1, h3 is Heading 2, h4 is Heading 3.
- For Word output, use native paragraph styles (Title, Heading 1–3, body) and lists, and right-aligned tab stops for dates, not spaces or layout tables. Set fonts, colors and tabs explicitly and remove inherited theme borders.
- **Screening-software safety:** no photos, icons, sidebars, multi-column layouts, layout tables or text boxes. Contact information stays in the body, not a page header or footer. Text must be selectable.
- Long headings wrap in the left area without colliding with dates. Allow extra row height; never shrink type or abbreviate a title silently.
- Use one page if the relevant evidence fits; two when necessary. The reference is a one-page placeholder, not a content budget.
- Use flowing paragraphs, never fixed coordinates copied from the preview.
- Print or render US Letter at 100% scale with browser headers and footers off.
- Render every finished document, inspect every page, check reading order, clipping, headings and dates, and remove every placeholder. Then run the [automatic check](../../agents/stage-2-resume.md#automatic-check-before-delivery).
- Save application documents outside templates/ and outside the career record.

## Contact details

Read [career/contact.json](../../career/contact.json) for every résumé. The name is the title; the contact line holds location, email, phone and website (or LinkedIn), separated by vertical bars, using the exact stored values. Leave out a field that is empty. Wrap the contact line naturally rather than shrinking it. Tip: a dedicated email alias for applications (for example a plus-address) makes replies easy to filter.

## Personal signature (optional)

Some people end their résumé with a short line of identities or interests, for example "Engineer • Teacher • Marathoner". It is off by default. To use one, record the exact wording in the "Documents" section of [career/preferences.md](../../career/preferences.md#documents).

- Include it once at the end of a full résumé, after the last section. It does not replace skills or evidence.
- Centered, selectable Arial 9.5 pt with 12 pt leading, bullet separators, each multiword label kept together when wrapping.
- A centered 0.5 pt gray (#999999) rule sits 12 pt after the preceding content and 3 pt above the signature. Its width is the rendered text plus 0.25 inch on each side, capped at the body width. Measure with the real font.
- Normal document flow, never a page footer. Keep the rule with the signature, and never let it fall alone on a page.

## Entry examples

Formatting only; these add no career evidence.

- Employer (Heading 2): **[COMPANY]** with **[MON YYYY - MON YYYY]** right-aligned in matching 11.5 pt bold caps.
- Role (Heading 3, indented 14 pt): **[Selected Functional Title]** with **[Dates]** right-aligned in matching 10.5 pt bold.
- Client engagement (Heading 3): **[Client Company]: [Selected Functional Title]** with **[Dates]** at right.
- Short-form entry, one paragraph: **Example Bistro: Line Cook | Oct 2015 - Jul 2016:** Prepared and plated dishes during dinner service.
- Education, one paragraph per qualification: **Example University:** BA, Economics | **2014**
- Skills: [Tool] | [Method] | [Skill].

## Formatting verification checklist

- Each short-form employer, role or engagement is its own paragraph, with its identifying label, dates and colon bold and the description regular.
- Education institutions and graduation dates are bold; qualifications are regular.
- Every date matches its label's font styling.
- Long entries wrap inside their insets; headings and dates do not collide. With caps letter-spacing, right-aligned dates end at the margin, not beyond it.
- Dated lists run newest first.
- The gap below every section rule matches (6 pt); the signature rule gap is 3 pt.
- Every rendered page passes the pagination rules; page one shows the strongest relevant evidence.
- Extracted text follows reading order. `tools/resume_check.py` automates this and the other text-level checks; see [Stage 2](../../agents/stage-2-resume.md#automatic-check-before-delivery).

## Drafting structure for agents

- Set the target role, scope (full résumé, selected employers or one section) and length before drafting. Allocate space by relevance and distinct evidence; choose the bullet count to show distinct evidence, not a fixed six or eight. Verify any page-share limit in the rendered layout; word count alone cannot establish it.
- Use only the role headings needed to show chronology. A supported functional title needs no formal-title disclaimer.
- Keep the user's format overrides. A template existing is not a reason to draft a résumé.
