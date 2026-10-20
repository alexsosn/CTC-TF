# #133 — Research: Agora's released Burns producer status

Snapshot 2026-10-20. CTC-TF `README.md` currently claims Agora pins `f58b162197ad8f113b7cd6fc0088ae5dd39a096d` and `release tracking disabled`; the checked-in docs test enforces this obsolete claim.

Verified live upstream evidence (not only issue text):
- `alexsosn/Agora` `main` registry `cuc-burns` entry now pins exact `ed6c7059803ff1adee057f5bd94d3ca661aac187`, `version: 0.3.0`, and `release_tracking: {mode: github-releases, channel: stable, tag_prefix: v}` after merged Agora PR #287 (`2b8e0c7326ebbc834c21aab68883732323593443`).
- `alexsosn/CTC-TF` public stable GitHub Release `v0.3.0` and lightweight Git tag resolve to the **same** commit `ed6c7059803ff1adee057f5bd94d3ca661aac187`. GitHub release has zero corpus assets.
- Agora producer remains `cuc-burns-csv` with `install_trust: explicit-code-execution`; the separate `CUC@tf/0.2.8` read-only parent and `network: deny` producer execution are unchanged. Existing local installations do not implicitly follow registry updates. Passive release discovery proposes reviews only, never executes code or rewrites a pinned runtime.
- Exact-head real integrated Agora E2E `38262395123` previously passed on #287: 45 Workbooks, 13,857 source rows, 10,419 annotations, 5,909 CUC lexical carriers, unchanged 146,017 slots/182,016 nodes and CUC warp; Context-Fabric MCP counted 5,909 `burns_headword_1` carriers.

This is docs/test maintenance only. No new corpus workflow, conversion semantic changes or additional dependency management is justified.
