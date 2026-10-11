# #115 Plan — evidence aggregation, not fuzzy matching

1. Research current aggregation functions, the synthetic fixture for repeated citations and mixed workbooks, and full-source acceptance checks (read-only source processing).
2. **Preserve RED:** add synthetic assertions for the per-class `one_missing_hypotheses` data contract. A repeated citation of one annotation must contribute 2 occurrences but 1 independent annotation. An out-of-order exact-hit example must remain independently marked as out-of-order even if its missing token has a unique local candidate. Ensure output JSON contains no source text or IDs.
3. **Minimal GREEN:** while processing the existing eligible gap loop, track class-specific annotation IDs and their occurrence counts, workbook ordinal annotation sets, and exact-hit order. Publish only integer/histogram aggregates; no changes to matching, exclusions, TF output, or report licensing.
4. Cross-validate class totals against existing `classes` and `one_missing_local_evidence` keys in the full-source acceptance; fail if the new cross-tab disagrees.
5. Run exact-head Python 3.10/3.12/3.13, real pinned licensed Burns Workbooks + reviewed CUC + Agora Bubblewrap, and Context-Fabric/reviewed CUC checks. Examine aggregate results only, without private lexemes or locators.
6. Independently adversarially review the actual diff, source-safe payload, reproduction/multiplicity, order confounding and CI output; post review as `COMMENT` on exact head. No production matching or post-release merge until v0.3.0 release gate is satisfied.

## Review-derived RED/GREEN: avoid cross-class double-counting

- Preserve synthetic RED `c9c0b17`: one authored annotation can yield one containment and one edit1 diagnostic on different citations. Per-class annotation sums must not be reported as the unique union.
- GREEN `9157f57`: add fixed-schema `one_missing_hypothesis_union` with occurrence total, distinct annotation union, and number of annotations appearing in both classes, using in-memory identity sets only.
- Real source cross-check `eefcb415`: verify union reconciliation and bounds; inspect actual aggregate CI result without emitting source strings or locators.
- Rerun exact-head Python matrix/real-source checks and renew the independent review on the final SHA. No merge before publication.
