# Issue 52 research: reviewed-CUC local quickstart

## Current user path

Reviewed base: `4994a45c53a73c09a4939731bc56af585b3ba30a` (the frozen v0.3.0 release candidate).

README already documents:

- Python 3.10+ installation from a repository checkout with `python -m pip install .`;
- the primary `ugarit-context-parsing module` CLI;
- CSV and PDF module commands;
- the exact reviewed CUC identity `DT-UCPH/cuc@ad69400f5446e1c8217af01659c7c10ab00c015b`;
- Text-Fabric path/version `tf/0.2.8`;
- that the converter does not download CUC automatically;
- the current Agora limitation.

The usability gap is that examples still use `/path/to/cuc/tf/0.2.8`, so a new user must infer how to acquire the exact parent tree safely.

## CUC identity

The reviewed commit exists upstream and is immutable:

- repository: `https://github.com/DT-UCPH/cuc.git`;
- commit: `ad69400f5446e1c8217af01659c7c10ab00c015b`;
- TF directory passed to Burns: `cuc/tf/0.2.8` after checkout.

At research time upstream `main` points to this exact commit. The documentation must nevertheless remain correct after normal upstream advancement rather than relying on this commit continuing to be an advertised branch tip.

Burns independently validates the reviewed required CUC files by exact size/SHA-256 and validates the expected Text-Fabric structure/counts before alignment. Acquisition therefore does not become a new trust bypass: an incorrect/incomplete checkout fails before module publication.

## Acquisition options considered

### Full clone + checkout

`git clone` followed by `git checkout --detach <sha>` is easy to understand and remains valid while the reviewed commit is retained in normal upstream history, but a normal clone downloads historical file contents unnecessarily.

### Archive URL

A GitHub commit archive avoids history, but introduces `curl`/archive extraction and a SHA-derived directory or tar-specific path manipulation. It is less uniform with ordinary Git-based workflows and makes local commit inspection less direct.

### Raw-SHA shallow fetch — rejected after adversarial review

The first GREEN draft used an empty repository plus:

```bash
git -C cuc fetch --depth 1 origin ad69400f5446e1c8217af01659c7c10ab00c015b
```

This works while the SHA is advertised/reachable under the server's fetch policy, including the current state where it is `main`. Long-lived documentation should not depend on a hosting service continuing to permit direct wants for a raw object ID after refs move. The reviewed identity is a commit, but acquisition should use normal repository history semantics rather than a raw-object fetch assumption.

### Blob-filtered clone + exact detached checkout — selected

Use a partial clone that omits historical blob contents, then checkout the reviewed commit explicitly:

```bash
git clone --filter=blob:none --no-checkout https://github.com/DT-UCPH/cuc.git cuc
git -C cuc checkout --detach ad69400f5446e1c8217af01659c7c10ab00c015b
git -C cuc rev-parse HEAD
```

Properties:

- explicitly checks out the immutable reviewed commit rather than whatever `main` points to at use time;
- remains usable after ordinary upstream advancement because the reviewed commit remains in repository history;
- `--filter=blob:none` avoids downloading historical file contents and fetches the checked-out blobs on demand;
- keeps network acquisition visibly outside the converter;
- leaves a normal Git worktree whose exact HEAD can be inspected locally;
- produces the stable path `cuc/tf/0.2.8` used by the module command.

Burns' own fingerprint verifier remains the authoritative product gate for the CUC TF files; the Git commands are a reproducible acquisition recipe, not a bypass.

## Installation boundary

This issue does not change packaging or claim a release that does not yet exist. The quickstart can use `python -m pip install .` from a repository checkout. Once `v0.3.0` is actually published, a later documentation edit may additionally show a tag-pinned Git install, but this issue must not fabricate that publication state.

## Data/license and Agora boundaries

- CUC acquisition is separate from Burns source acquisition; neither is bundled with this repository.
- CUC retains its upstream license.
- Burns Workbooks remain under CC BY-NC-ND 2.5 and generated Burns-derived artifacts remain user-local.
- The quickstart must not imply Agora can currently acquire/bind CUC for the parent-aware module. Current Agora registration remains the two legacy one-source materializers.

## Merge ordering

Prepare and review this documentation change independently, but do not merge it before the frozen `v0.3.0` release candidate is actually published. This avoids moving `master` while the first release still needs to be created at exact SHA `4994a45c53a73c09a4939731bc56af585b3ba30a`.

## 2026-10-11 current-master research correction

The preceding sections record the historically accurate pre-v0.3.0 work;
several old statements are now superseded. Actual master `81cc9a6c4a233bbc06b5349515a5a466497d274d`
renamed the module section to `## Feature-only module over reviewed CUC`,
removed the standalone row-slot materializer, and now advertises Agora #175's
`cuc-burns` **local-module** consumption (NOT legacy one-source producer
registration). Agora #135 still tracks full trusted-parent source orchestration.
The GitHub Release/tag v0.3.0 remains unpublished, and the currently reviewed
release candidate is `81cc9a6c4a233bbc06b5349515a5a466497d274d`, not the early SHA `4994a45c`.
The merged README must inherit master wording and insert only the reviewed
Git partial-clone+detached-checkout recipe. The exact CUC commit and immutable
TF fingerprints are unchanged. This remains post-release documentation.

## Independent post-rebase adversarial finding: repository contamination

Review against actual current-master `.gitignore` (not just initial design)
shows only `output/**/*.csv` and PDF sources are ignored. It does **not**
exclude a nested `cuc/` Git worktree or a generated `tf/burns-module/`.
The current quickstart instructs cloning the entire external CUC tree and
writing restricted Burns-derived feature files inside this software checkout,
making accidental staging/commit of CUC or licensed derived data possible.
This is a real reproducibility/distribution risk independent of the core
module's own safety. Rework the quickstart to use explicit `$HOME/data/...`
locations outside the checkout and make the Bash block abort on any failed
clone/checkout/fingerprint preflight. Preserve user-local input `output/`
from the previously documented extraction step. A synthetic docs-only RED
must catch the old in-repository paths before GREEN.

## 2026-10-11 post-Agora integration availability correction

The original README claim that Agora cannot execute a parent-bound Burns materializer is obsolete; actual upstream Agora code and docs were checked:

- Agora PR #238 merged as `977007363a1b446e9e786cd465ee16574f2ce8f7`. `registry/materializers.yaml` pins `cuc-burns` to immutable `CTC-TF@f58b162197ad8f113b7cd6fc0088ae5dd39a096d`, `cuc-burns-csv`, v0.3.0; it requires `install_trust: explicit-code-execution` and disables GitHub release tracking.
- Agora PR #240 merged as `3ccf58d60bbdd62d1fad7ef6c66ac726eee0ed43`. Public `scripts.agora_compose_feature_module` CLI and `wiki/guides/cuc-burns-managed.md` document `python scripts/agora_install_materializer.py fetch cuc-burns`, separate explicit `install cuc-burns --approve-code-execution`, then `python -m scripts.agora_compose_feature_module --module cuc-burns --source /absolute/path/to/burns-csv`. This uses managed reviewed CUC, OS sandbox, local Workbooks and does not automatically run on discovery.
- Actual Agora CI workflow `ctc-burns-registered-e2e.yml` exercises the approved producer, all 45 Workbooks, Text-Fabric composition and public Context-Fabric MCP query. Open umbrella #135 does not mean the scoped CLI is missing.
- CTC-TF GitHub release/tag `v0.3.0` remains absent. Agora's producer registry pin is an immutable, reviewed but **unreleased** CTC commit, and release tracking is disabled.

Documentation should now distinguish the native user-provided CUC quickstart and the optional Agora catalog-managed CLI. Link Agora's guide rather than duplicating commands. No claim of automatic licensed Workbooks acquisition, Windows sandbox, extra TF nodes or released producer version.


## 2026-10-12 release-state reconfirmation after workflow_dispatch

Live GitHub release and Git-data ref responses now establish that **v0.3.0 was published** at 2026-10-12T12:19:33Z: `refs/tags/v0.3.0` has direct commit target `ed6c7059803ff1adee057f5bd94d3ca661aac187`, the public non-draft/non-prerelease Release reports the same target and contains zero attachments. Current master has advanced after publication as post-release PRs merge. In contrast, the separately reviewed Agora registry still pins the earlier immutable producer `f58b162197ad8f113b7cd6fc0088ae5dd39a096d` and `release_tracking.mode: disabled`; publication alone does not automatically update registry execution identity.

Adversarial documentation finding: the existing README's phrase `release tracking disabled pending the separate GitHub v0.3.0 publication and registry-pin review` is now factually wrong about publication. Update it without implying Agora already tracks releases, upgrades automatically, or changes its pinned producer; preserve the independently verified copy-paste native quickstart and all license/parent boundaries. This is a docs-only release-state correction and requires a preserved focused RED assertion followed by GREEN and exact-head CI review.
