# #97 Plan

## Gate 1 — RED

Add source-safe tests for:
- substitution code-point pair;
- CUC insertion at start/internal/end;
- CUC deletion at start/internal/end;
- two distance-1 candidates remain ambiguous and are not counted as unique;
- higher-priority unique containment is excluded;
- expression syntax is excluded;
- payload contains no lexical strings/ids/locators/nodes.

## Gate 2 — GREEN research implementation

Add `aggregate_one_edit_research()` to the audit script. Restrict it to the
same hierarchy that yields #81's `unique_single_token_edit1` class. Do not
modify production alignment.

## Gate 3 — pinned real source

Assert the audit occurrence count equals #81's 112-class count. Record top
code-point confusions, positions, annotation independence and workbook
concentration.

## Gate 4 — follow-up

Create narrow bugs only for recurrent, independently evidenced parser or
transliteration conventions. Keep all other one-edit relations unresolved.

## Gate 5 — exact-head adversarial review

Challenge hidden fuzzy matching, direction mistakes, Unicode normalization,
ambiguity collapse, source leakage and repeated-reference inflation.
