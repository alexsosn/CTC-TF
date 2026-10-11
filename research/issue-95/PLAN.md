# #95 Plan

## Gate 1 — RED research contract

Add a source-safe `aggregate_token_boundary_research()` test covering:
- Burns 2 tokens → CUC 1 word (`merge`);
- Burns 1 token → CUC 2 words (`split`);
- equal token counts with shifted character boundary (`resegment`);
- repeated exact-concatenation windows counted as `2+`;
- non-boundary residual excluded;
- expression-syntax residual excluded;
- no source strings/ids/locators/nodes in payload.

## Gate 2 — GREEN audit

Implement the aggregate on clean/marker-only `HEADWORD_NOT_FOUND` occurrences.
Reuse production candidate tokenization and exact CUC line data. Do not modify
alignment.

Add it to pinned real Workbooks CI and assert its occurrence count agrees with
the #81 token-boundary probe.

## Gate 3 — interpretation

Record the 19-case direction/signature distribution and workbook concentration.
If a repeated deterministic family is visible, create a narrow implementation
ticket. Otherwise leave production unchanged.

## Gate 4 — local evidence

Provide an explicit local-only diagnostic path for manual inspection if needed.
It must never be enabled by CI or upload/commit source-derived lexical strings.

## Gate 5 — exact-head review

Challenge accidental whitespace-insensitive production matching, parser
corruption masquerading as segmentation, repeated-window ambiguity, source
leakage, and denominator drift from #81.
