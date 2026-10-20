# #114 — Research: out-of-order exact-token residuals

## Current code and frozen real-source evidence (2026-10-20)

The approved native feature-only Burns-on-CUC product remains aligned only by `headword_candidates` + exact contiguous `CUC g_cons` spans. In `scripts/audit_burns_alignment.py::aggregate_multitoken_residual_research`, the source-safe research probe takes clean/marker `HEADWORD_NOT_FOUND` annotations with at least two tokens, excludes exact neighboring-line candidates and exact concatenated token-boundary windows, and uses a **consuming** presence mask so repeated Burns tokens cannot reuse the same CUC word. It tests observed exact tokens for order via `_is_subsequence`, without promoting a lexical match.

Reviewed real Workbooks (45 private source files) and reviewed CUC 0.2.8 showed **380 multi-token residual occurrences** and **19 out-of-order exact-hit occurrences** among them. The 19 are source/line citations, not necessarily independent Burns annotations. Existing aggregate `exact_hit_order` has counts but no scoped distinct-annotation or multiplicity breakdown; `classes` cannot reveal how many reordered hits coexist with a one-missing containment/edit-distance hypothesis. Per-workbook independent counts are similarly missing.

The existing #115 source-safe research established why adding per-class distinct annotations without cross-class reconciliation can inflate evidence. #114 must similarly report **cross-class union** of the 19 reordered citations, with per-class counts and an explicit overlap figure if applicable, or avoid assigning independent annotation evidence to a specific morphology rule. Do not publish headwords, KTU locators, CUC strings, node IDs or annotation identifiers in CI.

## Bounded choice

Add a nested aggregate `out_of_order_research` only for residuals already classified `out_of_order`, containing occurrence count, distinct annotation count, occurrence multiplicity, per-workbook unique annotation counts, and disjoint **occurrence** classes plus class-specific annotation distinct counts and their union. No change to how matching, classification, suffixes, candidate evidence or TF publishing works.

Use a synthetic fixture with one Burns annotation cited at multiple out-of-order lines, plus an independent annotation, and a third in-order control, to prevent counting citations as separate lexical attestations. Retain the existing exact-head real licensed-source CI workflow to verify 19 old diagnostic occurrences remain and obtain new aggregates without releasing copyrighted examples.

**Decision:** This enables better prioritization of manual/source-private review; it does **not** authorize automatic reordering, partial expression matching, fuzzy edit, or realignment.
