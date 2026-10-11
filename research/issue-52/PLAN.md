# Issue 52 plan: copy-paste reviewed-CUC quickstart

Research: `research/issue-52/RESEARCH.md`.

## Phase 1 — docs contract RED

Add `tests/test_reviewed_cuc_quickstart.py` only.

The README materialization section must contain one copy-paste local sequence that includes all of these exact product constraints:

1. project installation via `python -m pip install .`;
2. CUC remote `https://github.com/DT-UCPH/cuc.git`;
3. exact reviewed commit `ad69400f5446e1c8217af01659c7c10ab00c015b`;
4. explicit detached checkout of the reviewed commit;
5. module invocation using `--cuc cuc/tf/0.2.8`;
6. an explicit sentence that CUC acquisition is a user action and the converter itself does not download CUC;
7. no wording that claims the parent-aware module is currently installed/executed by Agora.

Keep the test semantic enough to tolerate ordinary Markdown line wrapping; do not assert the whole README byte-for-byte.

Expected RED: the original README already has installation/module/CUC identity and the no-auto-download statement, but lacks the actual CUC acquisition commands and still uses `/path/to/cuc/tf/0.2.8` in examples.

## Phase 2 — initial GREEN

Change README only:

- insert a short `Quickstart` immediately under the CUC materialization section;
- show install → exact CUC acquisition/detached checkout → CSV module command;
- keep the detailed CSV/PDF subsections below it;
- replace placeholder CUC paths so the runnable examples use the acquired `cuc/tf/0.2.8` tree;
- preserve the existing exact compatibility/fingerprint explanation, licenses, and Agora-status section.

Do not change package/runtime/manifest/version/CI behavior.

## Phase 2b — adversarial acquisition review

After the initial GREEN, challenge whether the documented acquisition remains correct after upstream refs move.

Review finding: a shallow `git fetch origin <raw SHA>` can depend on server policy for direct wants of object IDs after that SHA stops being an advertised ref tip. Do not leave that as the long-lived quickstart contract.

Preserve a focused review-derived RED requiring instead:

- `git clone --filter=blob:none --no-checkout https://github.com/DT-UCPH/cuc.git cuc`;
- `git -C cuc checkout --detach ad69400f5446e1c8217af01659c7c10ab00c015b`;
- no raw-SHA `git fetch --depth 1 origin <sha>` recipe.

This keeps ordinary Git history semantics while avoiding historical blob downloads. Burns' own exact CUC fingerprint remains the authoritative validation gate.

## Phase 3 — exact-head CI and adversarial review

Run the normal repository test matrix and existing consumer/Agora contracts on one frozen head. Since this is README-only after the RED tests, no new external workflow is required.

Perform a logically independent adversarial review challenging:

- whether the commands really pin the exact reviewed CUC commit rather than `main`;
- whether acquisition still works after normal upstream branch advancement;
- whether network acquisition remains visibly outside the converter;
- whether paths are copy-paste coherent;
- whether the docs accidentally imply CUC/Burns redistribution or parent-aware Agora support;
- whether the quickstart is consistent with actual CLI argument order/options.

## Phase 4 — merge ordering

Do **not** merge before GitHub Release `v0.3.0` exists and resolves to exact commit `4994a45c53a73c09a4939731bc56af585b3ba30a`.

Once that release exists, refresh base if necessary, rerun exact-head CI if the base changed, then merge with expected-head protection after the independent review remains valid.

## 2026-10-11 current-master reconciliation amendment

The original PR HEAD was based on the now-obsolete pre-release README, whose
heading was `## Materializing a CUC-aligned Burns feature module`. Current
master `81cc9a6c4a233bbc06b5349515a5a466497d274d` has a different
`## Feature-only module over reviewed CUC` section, removes standalone
conversion, and documents Agora #175 local-module composition and #135's
unfinished managed resolver. A blind README merge would resurrect deleted
product claims and lose provenance guarantees. The actual CUC pin is unchanged.

- Review-derived RED: update the quickstart docs contract to locate the
  **current** heading, assert a normal blob-filtered Git clone, explicit
  detached `REVIEWED_CUC_COMMIT`, actual `module` CLI flags, and explicit
  local-source/Agora boundaries; assert `bash -n` syntax and no raw-SHA shallow
  fetch. Preserve the RED commit before merging master.
- GREEN: merge `master` into this draft branch with *master's* current README
  as base, inserting only the reviewed quickstart. Preserve all new release,
  Agora host, node/warp and licensing documentation unmodified.
- Exact-head all-six CI, real Workbooks/CUC/Agora and Context-Fabric;
  logically independent skeptical review. Maintain **draft/unmerged** until
  the GitHub tag+Release `v0.3.0` is really published, pinned to independently
  reviewed final release SHA `81cc9a6c4a233bbc06b5349515a5a466497d274d`
  (or a subsequently reviewed newer release candidate).

## Review-derived security/ergonomics subloop after first current-master GREEN

- **RED**: tests reject `git clone ... cuc` and `--output tf/burns-module`
  inside the source checkout because actual `.gitignore` does not exclude
  either. Require explicit out-of-repository `CUC_DIR` and `BURNS_MODULE`
  paths, and a fail-fast bash subshell so later conversion cannot proceed if
  checkout or revision identity checks fail. Preserve the failing CI before
  changing README or older tests.
- **GREEN**: retain the partial Git clone, exact detached SHA, native module
  interface and licenses, but use `$HOME/data/cuc-reviewed` and
  `$HOME/data/burns-feature-module`. Run from Burns software checkout,
  using local `output/` CSVs; no implicit downloads by materializer.
- **Review**: inspect real Git commands and case of existing output paths;
  no Git staging of CUC/Burns. Keep PR draft until first stable Release exists.
