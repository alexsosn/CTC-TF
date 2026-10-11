# Issue #16: v0.3.0 release notes after reviewed Agora host integration

## Evidence / research (2026-10-11)

Reviewing merged producer #122 (`f58b162197ad8f113b7cd6fc0088ae5dd39a096d`), the package and root Agora manifest both declare version `0.3.0`. The repository now has a legitimate manifest-specific adapter `ugarit_context_parsing.agora_adapter` for Agora's already-created empty output staging root; the public `ugarit-context-parsing module` still demands an absent output. Old `convert` standalone row-slot product is removed and must not be advertised/reintroduced.

Actual real data CI: reviewed immutable Agora host `21ae75d...`, pinned actual CUC release `0408967b1808c1f22c69e299d302b1e7b5e26354`, 45 licensed Burns Workbooks CSVs (13,857 source rows), 10,419 annotations, 69 feature-only TF files, 5,909 existing CUC lane-1 carriers, parent unchanged 146,017 slots and 182,016 total nodes, read-only CUC mount, Linux Bubblewrap source/output separation; run `38094501415` completed GREEN. Also exact-head Python 3.10/3.12/3.13 and five other workflows completed GREEN on PR #122. Independent final skeptical review `5481166183`; code merged as `f58b162...`.

Existing `docs/releases/v0.3.0.md` predates this manifest and falsely says a source+parent registered adapter is not present. It correctly records no Burns data redistribution, native feature-only weft, public absent-output semantics, previous six-feature `module-v1` compatibility and source-scoped scholarly caveats. Version `0.3.0` was already selected but **no release/tag exists yet**, as verified from GitHub releases and tags. Do not claim the GitHub release exists in notes/issue until publication is independently confirmed.

## Plan / preserved RED + GREEN

1. Add a RED release-contract test requiring that notes cite the **new** Agora manifest, its `cuc-burns-csv` materializer ID, the adapter name, pinned CUC revision, real 45-Workbook Agora sandbox evidence and explicitly distinguish code merge from **future** GitHub release / Agora registry registration.
2. GREEN minimally update the long-form release notes to accurately describe that restricted local-source parent-bound materialization now exists, while remaining **unregistered/unreleased** by Agora and never automatically fetching Burns data.
3. Keep software MIT vs Burns CC BY-NC-ND 2.5 rights and no data attachments, and no false claims of LXX/CATSS or full shared-parent multi-module orchestration.
4. Verify final-head unit suite and relevant real CUC/Workbooks workflows; logically independent skeptical review checks docs vs actual merged manifest/host output.
5. After merge: an authorized release creator must independently review final master exact SHA and publish GitHub tag+Release `v0.3.0` **pointing to that exact final reviewed merge commit**. GitHub connector in this workflow provides read-only Releases APIs but no create-release/tag action, so do not fabricate publication. Only then update Agora registry source SHA and enable release tracking via a separate reviewed PR.

## Explicit bounds

The real host smoke runs the reviewed `host.materialize` with the manifest and a validated parent input. It does **not** demonstrate complete Agora automatic installer, source approval or shared-module cache orchestrator; upstream manifest availability is a prerequisite rather than the full post-1.0 user-experience gate #135.

## Review-derived revision alignment (after #125)

The research above describes the **historical** first Agora host acceptance run before the reviewed-CUC SHA alignment. PR #125 was subsequently merged on 2026-10-11 at `322bfa0e96900f2888c102375da77f655b697bcd`, correcting the host's CUC checkout and trusted parent receipt to the same canonical revision enforced by `REVIEWED_CUC_COMMIT=ad69400f5446e1c8217af01659c7c10ab00c015b`. GitHub compare shows the intervening older→reviewed CUC commits affect README/logo only, but exact Git source identity is still a release invariant.

Review-derived RED `665f02b0ca47b55a71b9d3d1465e43fd3adb6c71` updated the release-note regression to require the actual canonical reviewed CUC SHA and reject the obsolete SHA. The earlier PR was merge-conflicted with #125; Git Data API merge `35a3b52aea4eecbda6fbfbf0a9e13e9a12ceeadd` resolved onto master while deliberately retaining the RED, and actual GitHub Actions Python 3.10 job `114429964719` failed specifically because old release notes still named the obsolete SHA.

The real verified canonical parent is attested in host run `38124841439`, job `114426956833`: 45 licensed Workbooks, 69 native Burns feature files, 5,909 lane-1 CUC word carriers, original 146,017 slots and 182,016 nodes, unchanged CUC warp, `bubblewrap` sandbox, trusted parent revision `ad69400f...`. The later GREEN release notes must cite **that** run, not present the earlier run as current. Changes must remain source-safe and docs/test-only, with no corpus bytes or new TF nodes. Recheck every exact-head workflow and perform fresh independent adversarial review before merge; publishing a GitHub Release/tag is still a separate #16 gate.

## Publication-stability adversarial check

Release notes are preserved alongside a published GitHub Release and may be read after Agora registry status changes. A literal present-tense “not yet published” or “not yet registered” would become false. The final notes therefore describe GitHub Release publication and Agora producer registration as **separate distribution actions** whose live state must be independently verified; no runtime/materializer promises follow from the notes themselves. The regression checks that these transient phrases are absent. This is an amendment to the existing #16 plan, not a new issue.
