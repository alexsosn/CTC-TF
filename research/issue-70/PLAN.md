# Issue #70 plan: remove standalone `convert` from the feature-only release candidate

## Goal

Delete the independent Burns row-slot corpus product while preserving both CUC-attached module formats and all post-#82 lexical/audit work.

## Research → RED → GREEN → full gates → independent review

1. Start from current `master@c9a812ab36c0145e7437f9b89b1530a9e9792060`.
2. Preserve RED asserting:
   - CLI help has no `convert`;
   - `convert` is rejected as an unknown command;
   - `graph`, `report`, `writer`, `_semantic_compare` are not importable;
   - `agora.materializer.json` is absent;
   - README/v0.3.0 do not promise standalone conversion or old materializer IDs.
3. Remove only standalone runtime imports/parser/dispatch/implementation modules.
4. Delete the obsolete upstream Agora manifest and its legacy-only validator job.
5. Remove the generic row-slot Context-Fabric consumer job/helper while preserving the dedicated feature-only CUC module/cfabric gates.
6. Split mixed tests so CSV/PDF source loading and identifier behavior remain covered under source-focused tests; delete standalone graph/report/publication/determinism assertions.
7. Update README, prospective v0.3.0 notes, release contract and Agora-status documentation for the `cuc-burns`/parent-resource boundary.
8. Keep every newer feature-only lane/span, headword candidate, line-drift, residual lexical-gap and real-source workflow untouched.
9. Run the complete current release-surface CI matrix on one exact head.
10. Perform a logically independent adversarial review of that exact head. Any material finding gets a review-derived RED before correction.
11. Mark ready and merge with expected-head protection only after all exact-head gates pass.

## Non-goals

- removing or redesigning `module-v1`;
- changing lane/span feature semantics;
- changing headword-expression candidate rules;
- changing alignment/audit heuristics;
- implementing Agora parent-resource orchestration;
- publishing v0.3.0 in this ticket.
