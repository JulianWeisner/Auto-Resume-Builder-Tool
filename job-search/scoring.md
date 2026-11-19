# Search screening and shared evaluation

Read [the shared evaluation standard](../agents/evaluation.md) for complete JD coverage, evidence ratings, grouping, weights and adjustment. New fully evaluated jobs use `shared-2` and its Promising / Stretch / Deprioritize label; historical runs retain their original policy. Search alone adds early screening and autonomous batch processing.

## Decision rules

- **Supported:** a mandatory ask is `supported` only at a score of 3 or 4. A score of 3+ may stay `unresolved` only for a threshold the records cannot settle (years, degree type, funding stage); write `threshold_note`.
- **Unmet:** use `unmet` only when dated records contradict the ask (for example 10+ years in a field against a recorded start date seven years ago). Write the record and computation in `contradiction`. Unmet does not exclude a job; the user confirms.
- **Classification** (mandatory sections, responsibilities, traits, restatements, domain, OR alternatives) follows [Classifying asks](../agents/evaluation.md#classifying-asks), the same rules Stage 1 uses. In search, an explicit qualification is `mandatory: true` with `mandatory_basis: explicit`; inferred concerns go in `inferred_concerns` or the card gap explanation. Each requirement's `kind` must match its `source_tags` (only `trait` may override); `pipeline.py` rejects a mismatch.

## Extraction before scoring

Split independent AND qualifications; keep genuine OR alternatives together. Merge restatements and record the merge. For each mandatory ask, retain the exact source quote and an explicit posting basis. Do not infer qualification status from a responsibility. Missing evidence remains unresolved, not a factual statement that the user lacks the skill.

During development, inspect a small sample for omitted or bundled asks. Source/quote checks establish traceability, not semantic completeness. Detailed audit reports are on request; normal delivery is cards and a short count summary.
