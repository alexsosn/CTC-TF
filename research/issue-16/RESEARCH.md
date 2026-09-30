# Issue 16 research: first stable release

## Current state

Reviewed base for this release slice: `237be081f2ba0ff17443aafebd09bbb1a4fa7a93`.

At that commit:

- package version in `pyproject.toml`: `0.2.0`;
- plugin version in `agora.materializer.json`: `0.2.0`;
- repository Git tag refs: none;
- repository GitHub Releases: none;
- repository software license: MIT, with PEP 639 package metadata;
- the public CUC-aligned `module` CLI is complete and tested;
- legacy `convert` remains available with an explicit deprecation diagnostic;
- README truthfully states that current Agora registration remains the legacy one-source materializers and parent-aware module registration is deferred.

Agora currently registers this plugin at commit `e1218b88d9d849c58ee25541339f32b0d8f5a7d3`, version `0.2.0`, with release tracking disabled and stale `software: NOASSERTION` metadata.

## Version decision

Use **0.3.0** / tag **`v0.3.0`**.

Earlier preliminary #16 research suggested 0.2.1 when the changes after the original Agora pin were only hardening/evidence. That conclusion is now obsolete: since then the repository has added a new supported public product surface, the CUC-aligned feature-module CLI, while retaining the old standalone converter for compatibility.

This is a backward-compatible feature addition rather than a breaking removal, so the next minor version is appropriate. Reusing `0.2.0` is also inappropriate because that version is already advertised by package metadata, the materializer manifest and Agora's registry even though no GitHub release/tag was ever created.

## Release identity contract

The release identity must align all upstream version-bearing surfaces:

- `pyproject.toml` project version: `0.3.0`;
- `agora.materializer.json` `plugin.version`: `0.3.0`;
- Git tag: `v0.3.0`;
- GitHub Release: published, non-draft, non-prerelease `v0.3.0`.

No CUC version changes in this release. Burns modules remain bound to reviewed CUC `0.2.8` at commit `ad69400f5446e1c8217af01659c7c10ab00c015b` through the exact compatibility fingerprint.

## Release scope

User-visible release contents:

1. **CUC-aligned Burns feature module** as the primary local product:
   - `ugarit-context-parsing module ... --cuc ...`;
   - feature-only output, no Burns warp;
   - conservative tablet/line/word/span alignment with explicit unresolved/ambiguous/out-of-CUC accounting;
   - lossless overlapping/multi-valued Burns annotations;
   - exact reviewed-CUC compatibility fingerprint in TF metadata/report.
2. **CSV and real PDF source paths** feeding the same reviewed module pipeline.
3. **Context-Fabric/cfabric-mcp composition** with CUC and Burns as separate locations, with CUC warp/navigation unchanged.
4. **Determinism and source-integrity evidence**:
   - repeated synthetic CSV semantic determinism;
   - real-parser synthetic PDF determinism;
   - environment/dependency evidence;
   - source-root/descendant symlink rejection.
5. **Legacy standalone compatibility**:
   - `convert` remains available but is explicitly deprecated.
6. **MIT software license**, separately scoped from Burns CC BY-NC-ND 2.5 source/generated-data restrictions.

## Explicit boundaries

The release must not imply:

- that Burns-derived CSV/PDF/TF data are redistributable under MIT;
- that any Burns source/derived artifact is bundled as a release asset;
- that CUC itself is bundled or relicensed;
- that current Agora can execute the parent-aware CUC module materializer;
- that the legacy standalone Agora materializers have been removed.

GitHub's automatic source-code archives are acceptable because the repository itself contains no Burns-derived source/generated artifacts.

No PyPI publication is part of #16 unless separately requested; this ticket's publication target is the GitHub release and Agora's immutable registry/release-tracking metadata.

## Agora release-tracking contract

Agora's stable materializer release tracker accepts only published, non-draft, non-prerelease GitHub Releases tagged `v<strict SemVer>`. It resolves the tag to an immutable commit and validates the exact `agora.materializer.json` at that commit before proposing registry changes.

After the upstream release exists, update Agora's `ugarit-context-parsing` registry entry to:

- `ref`: exact `v0.3.0` release commit SHA;
- `version`: `0.3.0`;
- `release_tracking.mode`: `github-releases`;
- `release_tracking.channel`: `stable`;
- `release_tracking.tag_prefix`: `v`;
- `licenses.software`: `MIT`.

Keep the registered materializer IDs unchanged because current Agora still exposes only the legacy single-input materializers. Enabling release tracking is passive discovery/review metadata and must not pretend parent-resource execution exists.

## Release evidence

Before publication, the release-prep PR must preserve a version-alignment RED and then pass all current repository gates on one frozen head. After merge, the **exact master commit that will be tagged** must also pass its push-triggered required workflows before the release is published.

Perform an independent adversarial release review on that exact release commit, challenging version identity, data/license boundaries, release notes, manifest stability, and absence of restricted assets.


## 2026-09-30 supersession: native-v2 release re-freeze

The earlier frozen candidate `4994a45c53a73c09a4939731bc56af585b3ba30a`
was never tagged or published. It was subsequently declared unsuitable for a
stable release after real user testing exposed #68: the feature-only v1 module
stored JSON annotation blobs/projections rather than a normal queryable native
Text-Fabric model. Issue #16 explicitly blocked publication of that candidate
on 2026-09-16.

PR #69 resolves #68 and was merged to `master` as
`f4ad420b68681665dbf5433f5cf11c1cd451b58e` after real Workbooks and Appendix
audits, reviewed-CUC/Context-Fabric/cfabric-mcp integration, conservative
lexical/reference boundary research, and an independent exact-head adversarial
review. Because no `v0.3.0` tag or GitHub Release exists, the SemVer identifier
`0.3.0` remains available; there is no published release identity to move.

The release candidate must therefore be re-frozen from native-v2 master rather
than publishing the abandoned feature-only candidate.

### Revised v0.3.0 product surface

The first stable release now includes:

- primary `module`: native-v2 extended CUC warp with first-class
  `otype=entity` Burns occurrence nodes;
- scalar queryable Burns entity features for source headword, supplied root,
  thematic category, semantic status, worksheet role and source section;
- tablet-scoped Burns findspot features only for unanimous Workbooks evidence;
- explicit `module-v1` compatibility command for the old six JSON-valued
  feature-module format;
- deprecated standalone `convert` retained for compatibility and current
  Agora one-input registration;
- exact reviewed-CUC 0.2.8 fingerprint/warp validation and native
  Context-Fabric/cfabric-mcp composition;
- real-source acceptance over 45 Workbooks / 13,857 rows / 10,419 annotations;
- separately pinned Appendix concordance evidence showing fragment ambiguity
  is not converted into invented fragment identity.

The release must not claim semantic completeness. Exact lexical entity
projection is deliberately limited to exact contiguous CUC `g_cons` spans;
unmatched headwords, ambiguous/partial references, unsupported source notation,
out-of-CUC annotations and non-textual records remain explicit local audit
evidence.

### Version decision after #68

Retain **0.3.0**. The version was prepared but never published. Native-v2 is a
material revision of the planned first stable release, but no user can depend
on a published 0.3.0 artifact/tag. Advancing to 0.4.0 solely to preserve the
identity of an unpublished rejected candidate would create a fictitious release
history. Package and manifest already agree on 0.3.0 and must remain aligned.

### New release-head gate

A new release-prep head after `f4ad420b...` must update the stale
`docs/releases/v0.3.0.md` and release research/plan before publication. Freeze
the exact resulting commit, then run all current gates, including the gates that
did not exist for the old candidate:

- Python 3.10 / 3.12 / 3.13 + installed-package;
- Agora manifest contract;
- generic Context-Fabric contract;
- reviewed-CUC index contract;
- native reviewed-CUC Burns + cfabric-mcp smoke;
- real pinned Burns Workbooks acceptance;
- pinned Appendix/CUC/Workbooks concordance audit.

A fresh independent adversarial release review must challenge release-note
accuracy, native-v2/v1 migration wording, restricted-data boundaries, exact CUC
identity, residual audit limitations, and absence of Burns-derived release
assets.

Post-v0.3 branches that name `4994a45...` as an exact release gate are now
stale sequencing documentation. They must be refreshed/rebased after the new
release is published; they must not force publication of the known-defective
candidate.
