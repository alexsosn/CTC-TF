# #114 Private case review — research (2026-11-10)

## Source-grounded deficiency

The pinned licensed Workbooks/CUC 0.2.8 acceptance confirms 380 eligible clean/marker multi-token residual citations and 19 citations with exact-hit words in the wrong order. The existing `aggregate_multitoken_residual_research` has safe occurrence counts, independent annotation counts, classes and cross-class overlap, exposed in the opt-in `--research-multitoken` CLI (merged #139). The `--report` full alignment JSON is user-private but does not juxtapose the cited line's CUC `g_cons` word sequence with Burns tokens. Researchers cannot adjudicate those 19 actual source forms without writing an ad hoc join.

Existing code source: `scripts/audit_burns_alignment.py::aggregate_multitoken_residual_research` filters clean/marker multi-token HEADWORD_NOT_FOUND, excludes uniquely found neighboring exact lines and token-boundary windows, consumes duplicate exact words with `_multitoken_presence_mask`, and defines `out_of_order` iff matched exact tokens are nonempty and not an ordered subsequence of CUC word `g_cons` values. These predicates, not approximate morphology, define the private review population. The existing `_write_private_report` performs an atomic 0600 local write only for an explicit destination path.

## Research decision

Introduce `--private-out-of-order PATH`, a narrowly scoped **local-only** report of the existing out-of-order candidate population. Include per-case Burns headword/tokens, annotation/occurrence ID, original worksheet provenance, original KTU reference, resolved citation and the cited CUC word `g_cons` sequence, plus token presence mask. Preserve natural repeated citations as separate cases but explicit independent-annotation count. Do not inject case-level strings, IDs, KTU locators or CUC words into stdout, committed fixtures, CI logs or GitHub uploads.

Recompute the same classification predicates only for this opt-in private diagnostic and check occurrence count/independent-annotation count against the existing source-safe aggregator to fail closed on drift. Do not change the aggregate, alignment, TF features, CUC warp, or parse logic. This supports subsequent human/source-private philological adjudication; producing a list is not itself resolving #114.

## Risks and negative controls

Only the explicit `--private-out-of-order` path can receive restricted detail. Default stdout and `--research-multitoken` remain aggregate-only. Private file mode must be 0600 (POSIX) and output must be atomic; do not print the content or path in normal CI. Duplication of references must not inflate the distinct count, but must preserve all cited cases. Exact in-order, zero exact hits, neighboring exact rescue and token-boundary cases must remain excluded. No inference from `edit1` or containment is permitted.
