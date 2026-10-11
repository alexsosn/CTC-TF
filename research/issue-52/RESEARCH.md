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
