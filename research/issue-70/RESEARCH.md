# Issue #70 research: remove standalone `convert`

## Question

What must be removed for the deprecated Burns row-slot corpus to stop being a supported product, without deleting source parsing or the CUC-attached compatibility/native module paths?

## Current architecture

Agora v1.0.0 / Agora PR #175 removed the two registered standalone Burns materializers and registers `cuc-burns` as a CUC-attached local feature module. CTC-TF still exposed the old architecture upstream through four independent surfaces:

1. public CLI command `ugarit-context-parsing convert`;
2. `agora.materializer.json` entries for CSV/PDF standalone conversion;
3. standalone graph/report/writer implementation (`graph.py`, `report.py`, `writer.py`);
4. CI/tests/docs that treated the row-slot corpus as an active compatibility contract.

The standalone artifact is structurally different from both CUC module formats: it creates `record` slots plus `worksheet`/`section`/`entry` nodes and its own warp. It is therefore not an alternate representation of `cuc-burns`.

## Shared versus legacy-only code

The CSV/PDF source loaders, identifiers, normalization, alignment, CUC fingerprinting and module/native writers are shared or current and must remain.

The standalone graph builder, conversion report, standalone writer, semantic comparator, CSV/PDF standalone integration tests, and old Context-Fabric row-slot consumer contract are legacy-only. Current CUC consumer coverage lives in:
- `.github/workflows/test-context-fabric-burns-module.yml` for the CUC-attached v1 module;
- the reviewed-CUC/native entity workflows introduced by #69 for native v2.

`module-v1` in #69 is **not** the target of #70. It remains CUC-attached and is a separate compatibility decision.

## Agora manifest decision

Keeping an empty or misleading `agora.materializer.json` would imply an executable materializer contract that Agora no longer uses. The current managed parent-aware execution design is still tracked in Agora #135. Until that contract exists, the truthful state is to ship no upstream Agora materializer manifest rather than retain the obsolete one-source declarations.

## Release documentation

`docs/releases/v0.3.0.md` is not yet historical: no `v0.3.0` tag exists. It can therefore be corrected before publication instead of preserving a promise to retain `convert`.

## Integration / branch strategy

PR #69 is actively changing `cli.py`, README, module behavior and CUC-native acceptance. Implementing #70 from old `master` would produce artificial conflicts. #71 is intentionally stacked on #69 and should remain draft until #69 stabilizes/lands. The cleanup delta itself must be independently reviewed on the final stacked head.

## Risks

- accidentally deleting CSV/PDF source-loader coverage together with standalone publication tests;
- weakening CUC module/native consumer coverage when removing the old row-slot consumer job;
- leaving hidden supported references to old materializer IDs or `conversion-report.json`;
- confusing `module-v1` with the unrelated standalone row-slot corpus;
- false CI failures if the stacked base moves between pull-request event creation and GitHub's merge-ref construction.

## Evidence

The preserved RED commit is `721b3f88bd8f3fe928374356716bcf71fc15d984`. Actions run #400 fails before production changes because `convert` and `agora.materializer.json` still exist, proving the removal contract is active.
