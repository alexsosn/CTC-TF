# #98 Plan

## Gate 1 — RED aggregate contract

Add source-safe tests for:

- multi-token filtering: single-token gaps are excluded;
- candidate-aware neighbor evidence is excluded before current-line analysis;
- exact full-expression split/merge evidence is excluded;
- exact-token presence masks preserve Burns token position;
- one missing token with unique containment is counted separately;
- one missing token with unique edit-1 is counted only after containment
  precedence;
- multiple local candidates remain ambiguous diagnostics;
- zero-overlap cases are retained rather than forced into a near-match class;
- repeated references do not inflate distinct-annotation evidence;
- workbook/worksheet-role aggregates;
- payload contains no lexical strings, locators, ids or node ids.

## Gate 2 — GREEN research aggregate

After #96/#97 shared-audit work is stable, implement
`aggregate_multitoken_residual_research()` in the audit script.

Reuse:

- production `headword_candidates()`;
- #91 candidate-aware neighbor boundary;
- exact boundary probe from #95/#81;
- the diagnostic containment/edit-distance primitives only as measurements.

Do not modify production alignment or TF publication.

## Gate 3 — pinned Workbooks

Record:

- exact multi-token denominator;
- partial vs zero/full-reordered/full-noncontiguous partitions;
- presence-mask frequencies;
- unmatched-token-count distribution;
- one-missing-token unique containment/edit1 counts;
- ambiguous local-candidate counts;
- distinct annotation evidence for recurrent signatures;
- workbook/role concentration.

The aggregate must reconcile with the relevant #81 classes after excluding
single-token zero-overlap cases.

## Gate 4 — local/private interpretation

Inspect the highest-frequency signatures locally. Split parser, morphology,
tokenization or reference issues into narrow child tickets only when concrete
examples support one explanation.

## Gate 5 — exact-head independent review

Challenge:

- accidental token-level fuzzy alignment;
- double-counting one CUC word for multiple Burns tokens;
- leaking single-token #96/#97 cases into this denominator;
- neighbor or exact-boundary evidence being reclassified;
- repeated-reference inflation;
- source-data leakage;
- unsupported semantic claims from masks alone.
