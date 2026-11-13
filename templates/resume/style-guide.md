# Résumé style guide

[Templates](../README.md) · [Default résumé template](README.md)

This guide defines the default résumé's structure and choices: a single-column, screening-software-friendly layout. It defines appearance only, not career evidence or a fixed story count. The rendered [PDF](resume.pdf) is the visual reference; [preview.png](preview.png) shows the same page.

Typography, spacing, implementation and the manual verification checklist are in the [layout reference](layout-reference.md). The template applies them and the build checks them, so read that page only when changing the template, producing another format, or when the build cannot run. If you made your own template ([custom templates](../custom/README.md)), its style guide replaces this one.

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

Choose one supported functional title from each either-or set. Do not combine alternatives, claim formal promotions the records do not hold, move work between periods or sum overlapping dates. Sequential supported functional titles may read as a progression when they reflect real growth in responsibility (see [functional labels](../../schema/experience-schema.md#titles)); decide fresh for each résumé whether to show them as separate headings or one combined progression. Include supported completion years; leaving one out is a deliberate tailoring choice, not an invented date. Apply the user's [presentation preferences](../../career/preferences.md#résumé-presentation): title grouping, which credentials always appear and which only when relevant, and how years of experience are counted.

## Pagination

- Start with natural document flow. Do not insert a page break only to keep an entire employer or section together. Prefer breaks between roles or complete entries.
- Keep each heading with its context and first complete bullet or entry. Never strand a heading at a page bottom. When the build reports one, wrap the heading and its first entry in `<div class="keep">` (defined in the template) rather than forcing a page break.
- Keep individual bullets together when they fit on one page. For paragraphs that must split, leave at least two lines on each page.
- Avoid a final page with only a few trailing lines.
- Fix an awkward one-word final line through careful wording only where meaning is preserved.
- Do not shrink text or silently remove evidence to solve pagination.
- Check what the recruiter sees on page one. Do not bury the strongest relevant evidence just to preserve employer grouping.
- Before forcing a manual break, compare natural flow with a break between roles, and record the choice in `plan.md`, not the résumé.
- Verify these rules in the rendered output, page by page. CSS rules or successful text extraction alone do not prove it.

Implementation: in HTML, avoid breaks after headings and context and inside individual bullets, and let lists and sections flow. In Word, chain headings and context with Keep with next through the first bullet; do not chain every bullet. If a renderer strands a heading, group only the heading, context and first entry.

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

## Drafting structure for agents

- Set the target role, scope (full résumé, selected employers or one section) and length before drafting. Allocate space by relevance and distinct evidence; choose the bullet count to show distinct evidence, not a fixed six or eight. Verify any page-share limit in the rendered layout; word count alone cannot establish it.
- Use only the role headings needed to show chronology. A supported functional title needs no formal-title disclaimer.
- Keep the user's format overrides. A template existing is not a reason to draft a résumé.
