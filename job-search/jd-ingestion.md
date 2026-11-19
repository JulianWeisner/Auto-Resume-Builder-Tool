# JD ingestion reference

## JD ingestion (B5)
`jd_ingest.py` turns one job description into a source-verifiable artifact that both batch screening and Stage 1 use. It does not fetch jobs, classify requirements, score or touch career evidence.

**Two entry routes, one artifact.**
- *HiringCafe:* in a batch run, `hiringcafe.py extract` does this for every response in the session transcript. Otherwise the agent passes the description text, exactly as received, with the provenance it actually has (`provider_job_id` is required; `url`, `retrieved_at`, `response_id`, `response_sha256`, `retrieval_tool`, `representation`, `company`, `title` are optional). Display blocks, when the agent has them, go in `--display-blocks` as a JSON list of strings.
- *Employer posting (Greenhouse):* save the `boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>` response as received, derive text with `jd_ingest.py greenhouse-text raw.json` (derivation `gh-text-1`), and ingest as `greenhouse` with `board`, `provider_job_id` and `response_sha256`. Use it when the HiringCafe copy is truncated; nothing is retyped.
- *Pasted into chat:* the agent saves the pasted text and ingests it as `user_paste`. No provider ID, URL or timestamp is needed or invented; provenance is recorded as user-supplied.

```sh
python3 job-search/tools/jd_ingest.py ingest --source-type hiringcafe --input jd.txt --meta meta.json --out DIR
python3 job-search/tools/jd_ingest.py ingest --source-type user_paste --input - --out DIR < pasted.txt
python3 job-search/tools/jd_ingest.py lines DIR        # numbered lines with block ID and role
python3 job-search/tools/jd_ingest.py render DIR - --save tags.json > key.md <<'MAP'
...jd_key map...
MAP
python3 job-search/tools/jd_ingest.py validate DIR     # reopen and revalidate
```

`DIR` holds `jd.txt` (what `tools/jd_key.py` numbers and renders) and `artifact.json`. The source text is stored once: the canonical source is `jd.txt` minus the recorded insertions. Errors are JSON on stderr with stable codes (for example `invalid_utf8`, `wrap_fragment`, `split_remainder_uncovered`, `reconstruction_mismatch`); exit code 1 means invalid, 2 means usage.

**Normalization.** Insert-only: the adapter adds `\n` and nothing else. It never rewrites punctuation, collapses whitespace or edits wording, and every insertion is recorded with code-point, UTF-8 byte and normalized offsets (half-open). Bytes input must be strict UTF-8 (a BOM is kept); text input is encoded as UTF-8. Real source line breaks, including `\r\n`, are kept as they are.
1. *Display boundaries*, when supplied, are used only if each block matches the source verbatim and in order, separated by whitespace alone. A boundary without a source line break gets one synthetic newline. If alignment fails the adapter records why and falls back (or fails with `--require-display-alignment`). It never copies the plugin's display formatting into the source.
2. *Fallback:* each non-blank source line is one block. This is the normal case for pasted text.
3. *Wrapping:* lines longer than 100 code points get a newline after a space, before the next word; a single overlong token is never split.

**Flattened descriptions.** Some connections return a whole posting as one paragraph. A source line of 1,500 code points or more is split into sentence blocks: a new block starts after sentence-ending punctuation followed by a capital, digit or bullet, and before an inline bullet. The method is then `line_blocks+sentences+wrap`. Splitting only inserts line breaks, so reconstruction and revalidation are unchanged, and postings with normal line breaks are not affected.

**Provider stubs.** A HiringCafe or Greenhouse description under 25 words (for example a bare job ID) is recorded as completeness `insufficient` (basis `too_few_words`), whatever was asserted, and L1 reports it as `evaluation_error`. Fetch the employer's posting. Pasted text is not judged by length.

**HiringCafe truncation.** HiringCafe connector descriptions stop at about 12,000 characters and end with `…(truncated — read the full posting at URL)`. The adapter keeps the marker in the source, records completeness `truncated` with the continuation URL, makes the marker a non-selectable block and marks the cut-off last block `truncated_tail` (not selectable). A truncated JD is not a complete JD: report it as `evaluation_error` in a run, or get the full posting (for example pasted from the employer page) and ingest that. Without a marker, completeness is `unknown` unless the caller asserts it; `hiringcafe.py extract` asserts `complete` for every description without the marker.

**Lines, blocks, selections and tags.** These are different things:
- A *physical line* is a line of `jd.txt`; wrapping can make many.
- A *logical block* (`U001`, …) is one display block or source line. It is not necessarily one requirement.
- A *selection* is what one jd_key map line quotes: whole blocks, or an explicit quoted span (`"start" ... "end"`) that may divide a block into several requirements.
- A *rendered tag* (`Do-1`, `Want-2`) is jd_key's output for one selection.

`render` runs the guard first and calls `tools/jd_key.py render` only if it passes, because jd_key on its own accepts a map that takes some of a block's wrapped lines. The guard rejects:
- a line range without a quoted span that covers only part of a block (`wrap_fragment`);
- a span that takes part of one block and part of another;
- a split block with untagged words left over;
- a split that meets exactly at a synthetic wrap with no punctuation or connector;
- a `skip` that covers part of a block;
- any selection in a provider marker or truncated tail.

An intentional split with a quoted span is valid on fewer than all of its block's lines. jd_key's own checks (verbatim spans, coverage, overlaps, shorthand rules) still run afterward and are not weakened. On success `artifact.json` records the map and each selection's exact quote, offsets and hash.

**Revalidation.** `validate` reconstructs the source and requires the canonical hash, byte and code-point counts to match. It then rebuilds every derived field (insertions, blocks, lines, IDs, roles, artifact ID) from the reconstructed source and the recorded type, provenance, completeness assertion and width, and requires them to equal the stored ones. Stored selections must equal a rebuild from the stored map. The recorded `jd_key.py` hash is informational. Artifact files are deterministic: the same input and parameters give byte-identical files, and no environment metadata (paths, clock time) is written.

**Quote sources.** A requirement's `source_span.source` is `description` (the default: the quote must appear in the posting text, and `validate --artifacts` checks it) or `provider_metadata` (a value from the provider's listing fields, such as HiringCafe's location, workplace or pay; not checked against the text).

**Search-run link.** A job may carry `jd_artifact` (`artifact_id`, `canonical_sha256`), and a requirement may set `quote_status: "source_verified"` with `source` (`tag`, half-open `source` offsets inside that tag's selection, `quote_sha256`). `pipeline.py validate run.json --artifacts STORE` loads `STORE/<artifact_id>/`, revalidates it and checks the quote is the exact slice (or its whitespace-collapsed form). Without `--artifacts`, a `source_verified` claim fails rather than passing unchecked. Requirements without `quote_status` remain `unverified`, and existing runs validate as before. Scores, screening and review decisions are unchanged.

**When the adapter cannot run.** Use `tools/jd_key.py` directly (or type the key by hand) and leave requirements `unverified`. Never mark a quote `source_verified` or describe an artifact as validated unless `jd_ingest.py` produced and validated it.

**Fixtures.** `tests/fixtures/jd/` holds two HiringCafe connector descriptions (Red Ventures, StubHub), both truncated by the provider and transcribed by the agent into the files. `fixtures.json` records their provenance and hashes. The B2–B4 Peloton and second fixtures were not available; their reported hashes are kept in `fixtures.json` for comparison and are not reproduced by these tests.

