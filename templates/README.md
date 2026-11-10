# Templates

Layouts for the documents the tool produces. Templates define appearance only: their placeholder text is never career evidence, and finished application documents are saved outside this folder.

| Template | What it is |
|---|---|
| [Résumé](resume/README.md) | Default single-column résumé, built to be read by people and screening software, with its [style guide](resume/style-guide.md) |
| [Cover letter](cover-letter/README.md) | Default one-page letter that matches the résumé, with its [style guide](cover-letter/style-guide.md) |
| [Custom templates](custom/README.md) | **Optional.** Your own templates, built by your agent from example résumés or letters you like |

Writing rules that apply to every document live in [agents/writing/](../agents/writing/): [plain language](../agents/writing/plain-language.md) (ASD-STE100-informed style and removing formulaic AI phrasing) and [claim wording](../agents/writing/claim-wording.md) (strong, truthful bullets). The [screening-software check](../agents/screening-check.md) runs on every résumé before you see it.

## Which template is used

The default templates, unless the "Documents" section of [career/preferences.md](../career/preferences.md#documents) names a custom one.

## Tool files and your files

resume/ and cover-letter/ are tool files: tool updates may replace them, so do not edit them in your copy. Put your own designs in custom/, which tool updates never touch.
