# #81 Plan

## Gate 1 - RED aggregate contract

Add source-safe tests for:

- clean/marker-only filtering;
- neighbor-evidence precedence;
- exact consonantal sequence under different token boundaries;
- in-order noncontiguous exact tokens;
- reordered exact tokens;
- unique prefix/suffix/internal containment;
- unique one-edit candidate;
- partial and zero exact-token overlap;
- mutually exclusive classification sums to the denominator;
- workbook/worksheet-role aggregate dimensions;
- no lexical strings, ids, locators or node ids in aggregate output.

## Gate 2 - GREEN research implementation

Add `aggregate_residual_clean_gap_research()` to
`scripts/audit_burns_alignment.py`.

Reuse production `headword_candidates()`, the #91 neighbor boundary and the
existing CUC line index. Do not modify production alignment.

Add the aggregate to the pinned real Workbooks workflow and assert its
clean/marker denominator equals the corresponding current
`HEADWORD_NOT_FOUND` counts from the expression audit.

## Gate 3 - real-data interpretation

Record:

- 885-denominator closure;
- neighbor-evidence count;
- classification counts for the remaining current-line failures;
- token-boundary exact count and window sizes;
- single-token containment/edit-distance distributions;
- workbook/worksheet-role concentration.

Create separate implementation/parser issues for recurrent evidenced families.
Do not mix independent fixes into this research PR.

## Gate 4 - private diagnostics

If aggregate results identify a recurrent family that requires concrete examples,
add an explicit local-only diagnostic output path with owner-only permissions.
Never add source strings to CI output.

## Gate 5 - review

Exact-head adversarial review must challenge:

- leakage of expression-syntax failures into the denominator;
- treating neighbor evidence as morphology;
- fuzzy matching disguised as normalization;
- loss of ambiguity;
- source-data leakage;
- unsupported claims from aggregate string similarity.

Finalize research only after real-source and standard exact-head gates pass.
