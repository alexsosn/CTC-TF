# #91 Plan

## Gate 1 - RED

Extend `tests/test_line_address_drift_audit.py` with:

- a simple parenthesis expression whose cited line is a miss and +1 contains
  only the production `parenthesis_core`;
- a token-internal slash expression whose +1 line contains distinct left/right
  spans, requiring `ambiguous_neighbor_span`;
- a #79 opaque-inner-group expression whose neighbor matches only the outside
  `parenthesis_core_opaque_group`;
- existing literal, boundary, run-histogram, and source-safety tests unchanged.

The RED must fail because current audit uses literal `_headword_tokens`.

## Gate 2 - GREEN

Import and call production `headword_candidates()` inside the line-drift
audit. For each neighbor, union exact spans from all candidates and classify by
distinct-span cardinality.

Do not change production alignment code.

## Gate 3 - real Workbooks

Run the pinned real-source gate. Record old vs new residual line-drift counts and
syntax-class deltas. Update release/readme claims if any numbers change.

## Gate 4 - independent review

Review the exact final head from the diagnostic boundary:

- production/audit semantic equivalence;
- span deduplication;
- no first-hit behavior;
- no cross-column/tablet drift;
- no source strings in aggregate output;
- no production alignment/module changes.

Finalize only after exact-head tests and real Workbooks gates are green.
