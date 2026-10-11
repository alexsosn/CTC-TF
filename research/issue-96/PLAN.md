# #96 Plan

## Gate 1 — RED research contract

Add source-safe tests for:

- one unique CUC word with a right-side extra segment;
- one unique CUC word with a left-side extra segment;
- both-side/internal containment;
- multi-code-point extra length accounting;
- repeated containing CUC candidates remain ambiguous and are excluded;
- neighbor exact evidence takes precedence and is excluded from containment;
- repeated references do not inflate distinct-annotation evidence;
- expression-syntax cases are excluded;
- aggregate payload contains no lexical strings, locators, ids or node ids.

## Gate 2 — GREEN aggregate

After #97 is finalized, add `aggregate_containment_research()` to
`scripts/audit_burns_alignment.py`.

Reuse the exact same #81 hierarchy boundary. Do not modify production
`headword_candidates()`, alignment or TF publication.

## Gate 3 — pinned real Workbooks

Assert the aggregate occurrence count equals #81's
`unique_single_token_containment=108`.

Record:

- side distribution (expected baseline 64/41/3);
- extra-length distribution;
- extra code-point frequencies by side;
- distinct-annotation counts / multiplicity;
- workbook and worksheet-role concentration.

## Gate 4 — interpretation

Inspect recurrent top families locally against Burns and CUC. Create a narrow
child issue only when a relation is independently supported as morphology,
orthography, or parser normalization.

Do not promote aggregate substring patterns directly.

## Gate 5 — exact-head review

Challenge:

- hidden stemming/affix stripping;
- incorrect Burns->CUC direction;
- repeated-reference inflation;
- multiple containing candidates treated as unique;
- neighbor/address evidence leaking into morphology;
- source-data leakage.
