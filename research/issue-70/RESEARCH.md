# Issue #70 research: remove standalone `convert` on the current feature-only module topology

## Current state

`master@c9a812ab36c0145e7437f9b89b1530a9e9792060` has the corrected primary Burns product as a feature-only module over the reviewed CUC warp. PR #82 deliberately removed the experimental entity/extended-warp model. The current supported CUC-attached commands are:

- `module`: corrected lane/span feature-only CUC module;
- `module-v1`: explicit six-feature JSON compatibility module.

The deprecated standalone `convert` path is still present independently. It creates its own `record` slots and `worksheet/section/entry` warp, so it is not a compatibility encoding of either CUC module format.

## Legacy surface still present

Current master still ships:

- CLI parser/dispatch for `convert`;
- `graph.py`, `report.py`, `writer.py`, `_semantic_compare.py` supporting the row-slot corpus;
- `agora.materializer.json` with the two one-source standalone materializers;
- generic Agora/Context-Fabric CI jobs that validate only that standalone product;
- standalone determinism/materialization/integration tests;
- README and prospective `v0.3.0` notes promising that standalone conversion remains available.

## Release state

No `v0.3.0` tag or GitHub Release exists. Release notes remain prospective and can be corrected before publication.

## Agora boundary

Agora has already migrated Burns registration to the CUC-attached `cuc-burns` local-module path. The old one-source standalone materializers should therefore not remain an upstream product contract. Fully managed source+parent materializer execution remains a separate Agora parent-resource problem; removing the stale manifest must not be replaced by a fake one-input manifest.

## What must survive

- CSV/PDF source loading and validation;
- Burns normalization, headword-expression candidate parsing, alignment and audits;
- exact reviewed-CUC fingerprinting;
- corrected feature-only lane/span `module` implementation and report;
- explicit `module-v1` compatibility;
- all current real-source, reviewed-CUC, Context-Fabric/cfabric-mcp, headword-expression, line-drift and residual-gap research/acceptance gates.

## Legacy-only code/test boundary

`graph.py`, `report.py`, `writer.py`, `_semantic_compare.py`, the standalone row-slot consumer contract, and standalone materialization/determinism/integration tests have no role in the corrected feature-only product. Shared loader/identifier tests embedded in mixed legacy test files must be preserved under source-focused names.

## Risks

- accidentally deleting source parsing shared by `module`/`module-v1`;
- accidentally weakening the new lane/span feature-only consumer evidence;
- keeping stale release/Agora contracts that resurrect `convert` after code deletion;
- treating `module-v1` as legacy standalone even though it is CUC-attached;
- losing newer research/acceptance workflows introduced after #82.

## TDD gate

On the current master topology, preserve a fresh RED requiring the public CLI and installed package to have no standalone converter implementation, no upstream legacy Agora manifest, and no public release documentation advertising retained standalone conversion. Only after that current-master RED is observed should production cleanup land.
