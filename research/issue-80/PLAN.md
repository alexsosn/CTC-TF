# #80 Plan: source-safe neighboring-line drift audit

## Gate 1 — RED

Add a pure audit contract before implementation.

Synthetic fixtures must cover:

1. `HEADWORD_NOT_FOUND` on line N with a unique exact match at N+1;
2. unique match at N-1;
3. matches at multiple neighbor offsets -> `multi_neighbor`;
4. multiple exact spans on one neighbor -> `ambiguous_neighbor_span`;
5. no neighbor match;
6. missing neighbor lines are absent, not errors;
7. column boundary is never crossed even if adjacent numeric line exists in another column;
8. tablet boundary is never crossed;
9. bare-line occurrence uses reverse structural identity from the resolved context node;
10. non-`HEADWORD_NOT_FOUND` outcomes are excluded;
11. aggregate JSON contains no source strings/locators/section labels.

## Gate 2 — GREEN

Implement `aggregate_line_address_drift_stats(source, alignments, index)` in `scripts/audit_burns_alignment.py`.

Reuse the exact production lexical primitives (`_headword_tokens` and `_candidate_spans`) rather than reimplementing a subtly different matcher.

Do not modify:

- reference grammar;
- `align_burns_source`;
- `_candidate_spans`;
- CUC index construction;
- TF publication.

Add the aggregate to `scripts/check_real_burns_source.py` and invariant checks that its audited total equals the current `HEADWORD_NOT_FOUND` occurrence count.

## Gate 3 — real source

Run pinned Workbooks + reviewed CUC 0.2.8. Record aggregate results in this research file and #80.

Pay special attention to:

- total rescue rate;
- asymmetry of -1/+1 vs -2/+2;
- multi-neighbor collision rate;
- longest same-offset runs;
- rescue rate among clean/marker-only vs punctuation-bearing expressions.

## Gate 4 — decision

Do not implement line shifting from counts alone.

If a systematic cluster/run is material, create a child issue requiring source-edition evidence and RED/GREEN mapping tests.

If not, document line-address drift as a minor/non-dominant factor and continue with #78/#79/#81.

## Gate 5 — exact-head review

Perform a logically independent review grounded in the implementation and real-source output. Attack:

- accidental boundary crossing;
- reverse-index ambiguity;
- denominator leakage;
- counting multiple spans as multiple offsets;
- privacy leaks;
- any code path that mutates production alignment;
- CI path-filter coverage for the new audit semantics.
