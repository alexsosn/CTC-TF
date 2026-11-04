# #138 Research: safe access to multi-token residual hypotheses

## Observed implementation gap (2026-11-04)

The scripts/audit_burns_alignment.py command currently parses --cuc, optional --workbooks (local PDF Workbooks), and --report. It prints only aggregate_alignment_stats JSON by default. Its only full raw-source report is explicitly requested with --report and published owner-only.

The same module already implements aggregate_multitoken_residual_research. It accepts the normalized Burns source, existing alignments and reviewed CUC index that main() already constructs. It returns only aggregate counts and derived order/cardinality labels, including exact_hit_order, one_missing_hypotheses, one_missing_hypothesis_union and out_of_order_research. Annotation IDs are used internally for deduplication but are not returned. The tests/test_multitoken_residual_research.py suite includes distinct-annotation, repeated-citation, order and source-string privacy tests. These remain **diagnostic hypotheses**, not production lexical spans.

## Decision

Expose an **opt-in** --research-multitoken CLI flag, nesting the existing aggregate under multitoken_residual_research in the normal JSON. Without the flag, JSON shape and optional --report behavior must remain unchanged. Reuse the same source/index/alignment objects; do not recompute lexemes, add a parser, acquire extra files, create TF nodes, change alignment, or add dependencies.

## Validation / limitations

Synthetic test will call the actual CLI with local --workbooks and --cuc arguments, mocking only PDF acquisition and CUC loading to avoid restricted files, and exercising the actual normalizer, aligner and research aggregate. Verify nested classification and occurrence/independent-annotation counts, default absence, privacy and no implicit --report call. A private licensed 45-Workbook run and Agora E2E acceptance must pass on exact final HEAD. Baseline: 380 eligible multi-token residual occurrences and 62 one-missing unique hypotheses (23 containment / 39 edit-1); these are not independent morphological attestations.

Read-only CUC 0.2.8, feature-only TF over parent CUC warp, licensing boundaries, and production matching remain unchanged.
