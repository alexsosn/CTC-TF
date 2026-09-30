# Issue 16 plan: v0.3.0 first stable release

Research: `research/issue-16/RESEARCH.md`.

## Phase 1 — version-alignment RED

Add `tests/test_release_version.py` only.

The installed package and `agora.materializer.json` must both advertise the intended release version `0.3.0`. The test must use `importlib.metadata.version()` for the installed project so CI proves built-package metadata rather than merely parsing source TOML.

Also freeze identity invariants that release automation depends on:

- plugin id `ugarit-context-parsing`;
- plugin repository `alexsosn/ugarit-context-parsing`;
- materializer ID sequence remains exactly the two supported legacy Agora IDs.

Expected RED: current installed package and manifest both still say `0.2.0`; all unrelated converter/module tests remain green.

## Phase 2 — release-prep GREEN

Make only release metadata/documentation changes:

1. bump `[project].version` in `pyproject.toml` to `0.3.0`;
2. bump `plugin.version` in `agora.materializer.json` to `0.3.0`;
3. add `docs/releases/v0.3.0.md` with user-visible release notes covering:
   - the CUC-aligned `module` CLI as the primary local product;
   - CSV and real PDF source paths;
   - conservative CUC alignment and exact compatibility fingerprint;
   - Context-Fabric/cfabric-mcp composition;
   - determinism/source-validation guarantees;
   - deprecated but retained standalone `convert` path;
   - MIT software license vs Burns CC BY-NC-ND data boundary;
   - current Agora limitation: only legacy one-source materializers are registered.

Do not change source/parser/alignment/module code or materializer IDs in this phase.

## Phase 3 — frozen release-prep CI and review

Run every current repository gate triggered by the version/manifest change:

- Python 3.10 / 3.12 / 3.13 full suite;
- installed-package smoke and package metadata;
- Agora manifest contract;
- reviewed-CUC index/module contract;
- Context-Fabric/cfabric-mcp contracts;
- deterministic CSV/PDF tests already contained in the suite.

Freeze one head and perform a logically independent adversarial release-prep review. Challenge version identity, release-note accuracy, compatibility claims, materializer ID stability, and restricted-data boundaries.

Merge with expected-head protection only after that review is clean.

## Phase 4 — exact release-commit gate

The squash/merge commit on `master` becomes the candidate release commit. Do not tag immediately.

Verify the workflows triggered on that exact master SHA complete successfully. Independently inspect the exact commit tree and confirm:

- package/manifest = 0.3.0;
- MIT LICENSE/package metadata present;
- release notes correspond to 0.3.0;
- no Burns-derived CSV/PDF/TF files or other release assets are added;
- current CUC reviewed identity is unchanged;
- Agora-status wording remains truthful.

Record this release review on issue #16 with the exact SHA.

## Phase 5 — publication

Publish a non-draft, non-prerelease GitHub Release:

- tag: `v0.3.0`;
- target: the exact reviewed master commit from Phase 4;
- body: the reviewed `docs/releases/v0.3.0.md` content;
- no manually attached Burns-derived artifacts.

Verify the release/tag resolves back to the reviewed commit.

## Phase 6 — Agora registry follow-up

After the GitHub Release exists, update `alexsosn/Agora` in a separate reviewed change:

- registry ref → exact release commit SHA;
- version → `0.3.0`;
- `release_tracking.mode` → `github-releases`;
- stable channel / `v` tag prefix;
- software license → `MIT`;
- keep the same two registered materializer IDs and current one-source execution model.

Run Agora registry validation and release-discovery checks before merge. This follow-up does not unblock/deploy parent-aware Burns module materialization; #29 remains deferred until Agora restores that capability.

## Completion

Close #16 only after the upstream release is published and the reviewed Agora registry update is merged or, if repository permissions prevent that follow-up, explicitly document the remaining external blocker without misrepresenting release publication status.


## 2026-09-30 revised plan — native-v2 v0.3.0 re-freeze

The original release candidate at `4994a45...` is abandoned, not published.
PR #69 merged #68's native-v2 correction into master as `f4ad420b...`.
The remaining release work is a new research → plan → release-note RED → GREEN
cycle followed by exact-head CI/review.

### Phase 7 — release-note RED

Before editing `docs/releases/v0.3.0.md`, extend the release contract tests to
require that the v0.3.0 notes:

1. identify the primary `module` output as native-v2 entity nodes / extended
   CUC warp rather than a feature-only JSON module;
2. document explicit `module-v1` compatibility;
3. preserve the deprecated standalone `convert` / current legacy Agora
   boundary;
4. state that no Burns-derived artifacts are attached/distributed;
5. avoid the stale primary-product claim `feature-only Text-Fabric module`.

Expected RED: version identity remains green at 0.3.0, while the stale release
notes fail the new product-surface assertions.

### Phase 8 — release-note GREEN

Update `docs/releases/v0.3.0.md` only as needed to describe the reviewed
native-v2 release accurately:

- native entity nodes and scalar query features;
- exact reviewed CUC dependency and complete-warp extension semantics;
- real-source lexical/reference coverage boundaries;
- conservative tablet findspots and Appendix/fragment limitation;
- explicit v1 compatibility and standalone-convert migration path;
- Context-Fabric/cfabric-mcp evidence;
- current Agora parent-resource limitation;
- MIT software vs Burns/CUC data-license boundaries.

Do not attach or commit generated Burns-derived data.

### Phase 9 — release-prep PR and frozen exact-head gates

Open a release-prep PR from the native-v2 master. On one exact head require:

- Tests / Python 3.10, 3.12, 3.13 + installed-package;
- Agora contract;
- generic Context-Fabric contract;
- reviewed-CUC index contract;
- reviewed-CUC native Burns + cfabric-mcp smoke;
- Context-Fabric Burns module contract;
- real pinned Workbooks acceptance;
- Appendix/CUC/Workbooks concordance audit.

Perform a logically independent adversarial release review on that same SHA.
Any material finding gets a review-derived RED before correction.

### Phase 10 — merge and exact master release gate

Merge the release-prep PR with expected-head protection. The resulting master
commit, not `4994a45...`, becomes the sole candidate for `v0.3.0`.

Verify push-triggered workflows on the exact master SHA and independently inspect
the final tree for:

- package/manifest version = 0.3.0;
- release notes match native-v2 reality;
- MIT software licensing remains distinct from Burns/CUC data;
- no Burns-derived CSV/PDF/TF artifacts were added;
- exact reviewed-CUC identity is unchanged;
- Agora wording remains truthful.

### Phase 11 — publication and stale-stack refresh

Publish non-draft, non-prerelease `v0.3.0` at that exact reviewed master SHA,
with no manually attached Burns-derived artifacts. Verify tag/release identity.

Then refresh every post-release PR that still names `4994a45...` as its gate.
Rebase/retest them against the actual released master and repeat exact-head
independent review when conflict resolution or public routing changes behavior.
