# #115 Research — independent source evidence for one-missing-token hypotheses

## Baseline code and real-data evidence

The existing `scripts/audit_burns_alignment.py::aggregate_multitoken_residual_research` is a **source-safe diagnostic**, not a lexical matcher. For eligible clean/marker `HEADWORD_NOT_FOUND` occurrences, it excludes neighboring exact matches and exact concatenated token-boundary windows, then produces exact-token presence masks and disjoint classes. The reviewed real dataset has 380 such multi-token residual occurrences, 62 one-missing **unique local candidate** cases (23 containment, 39 edit-distance-1), and 19 out-of-order exact-hit cases in the full 380.

It already exposes overall `distinct_annotations`, global `annotation_occurrence_multiplicity`, and per-workbook occurrence counts. **Missing:** independent annotation counts/multiplicities *within* each of the two one-missing unique classes, and a cross-tab showing which of their exact-hit subsets are in Burns order. The 62 occurrences cannot be treated as 62 independent examples of any morphological or editorial rule.

Code source: `aggregate_multitoken_residual_research` loops `alignment.occurrences`, with `annotation.annotation_id` and `annotation.workbook_number` available in memory. Its return payload must not expose either annotation IDs or source strings/locators/nodes; only counts and workbook ordinal aggregates.

## Research boundary

Add a **nested, source-safe aggregate** for `unique_containment` and `unique_edit1` only:
- occurrence count; distinct Burns annotation count;
- multiplicity histogram of occurrences per annotation;
- exact-hit order distribution independently for each hypothesis;
- per-workbook *distinct annotation* counts (not just occurrence totals).

These figures are about diagnostic candidates, not confirmed inflection, translation, editorial repair, or production alignments. Do not publish case-level Burns tokens, CUC forms, KTU/RS references, node IDs, source record IDs or annotation IDs. Keep the existing production rule set unchanged.

## Review requirements

Independently verify that repeated references from one annotation are not counted as distinct evidence, that order is computed from nonreused exact CUC matches, that categories reconcile with existing 23/39 counts, and that no source-derived string enters the aggregate. Run the actual private licensed-Workbooks acceptance to obtain and validate aggregate numbers; preserve a synthetic failing regression before implementation. Keep PR draft/unmerged until the frozen v0.3.0 release is published.

## Independent review-derived cross-class union correction

Even the two per-class independent annotation counts cannot safely be added: one Burns annotation can cite distinct CUC lines whose remaining token receives *different* unique candidate classes. A new synthetic source-safe regression (commit `c9c0b17`) creates one annotation with two citations (one containment and one edit1) and requires `occurrences=2`, `distinct_annotations=1`, `annotations_in_both_classes=1` for their union. The production diagnostic now reports the union's cardinality and overlap (integers only), not annotation IDs; the real Workbooks acceptance reconciles both classes with union counts. This is still hypothesis accounting, **not** attested morphology or permission for fuzzy matching.
