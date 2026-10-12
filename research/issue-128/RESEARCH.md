# #128 — Research: reviewable one-shot GitHub Release publisher

## Live release blocker

The linked GitHub connector exposes Git/commit/PR reads, but no tag or Release **creation** operations. Frozen reviewed `v0.3.0` candidate `81cc9a6c4a233bbc06b5349515a5a466497d274d` has no tag or GitHub Release as of 2026-10-11; #16 and post-release PRs cannot proceed. GitHub Actions supports manual `workflow_dispatch`, job-specific `permissions: contents: write`, and GitHub API access through `GH_TOKEN`.

GitHub REST [Create a release](https://docs.github.com/en/rest/releases/releases) warns that `GITHUB_TOKEN` cannot authorize releases when target commit adds/modifies `.github/workflows/` relative to default branch; therefore a new release workflow should NOT promise it can publish the older commit `81cc9a6...` after it has itself advanced `master`. Target the **new, reviewed, merge-commit default-branch HEAD** after merging this workflow (release gate reviews will attest exact new SHA). The workflow is never triggered automatically.

## Fail-closed controls

- Explicit input: full reviewed merge SHA and confirmation `v0.3.0@<full SHA>`. Demand `GITHUB_REF=refs/heads/master`, `GITHUB_SHA` equals input, and GitHub's live master ref equals input at preflight.
- Inspect exact merge commit's two parents; its second parent is the PR tip with the identical Git **tree** as merge commit. Demand all six named PR workflow checks succeeded on that exact tip, plus a master `push` Tests success on merge SHA; no trust from stale green workflow names alone.
- Fetch `pyproject.toml`, `agora.materializer.json`, `docs/releases/v0.3.0.md` **from candidate SHA** via GitHub Contents API. Validate package and manifest versions both `0.3.0`, parent-bound feature module, user-local source, no standalone conversion, and report that restricted licensed Burns data are excluded.
- Refuse a preexisting GitHub Release. Refuse a preexisting **wrong** tag; permit a matching tag for recovery if tag creation succeeded but release creation failed. Atomically create a lightweight git tag ref before creating the Release. Reverify its full target SHA before and after publication; do not upload assets.
- Manual publish only; default command is nonmutating preflight. No `push`/`schedule` publisher or ambiguous implicit `master` release target. Assume contents-write token may be blocked by repository settings: fail visibly, never assert success absent tag+Release.
- A tag could be created before Release API fails, leaving a safe exact-SHA ref. Rerun recovers the matching tag; never delete or retarget any tag.

## Boundaries / source evidence

- The pinning CI and Agora host evidence for v0.3.0 comes from actual pinned reviewed CUC `ad69400f5446e1c8217af01659c7c10ab00c015b`, 45 licensed runner-local Workbooks, feature-only 69 TF files / unchanged 146,017 slots and 182,016 nodes.
- `docs/releases/v0.3.0.md` uses distribution-step-neutral wording, so its bytes can be used unchanged both before and after publication. No Burns CSV/PDF/TF-derived bytes are committed or attached.
- This PR adds release **mechanics**, not Burns parsing, matching, node ownership, or Agora registry publication; existing #16 release gates still apply.
