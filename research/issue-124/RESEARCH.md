# #124 — Research: exact CUC pin drift in Agora host acceptance

## Source-grounded finding

- Canonical review constant: `src/ugarit_context_parsing/cuc_index.py::REVIEWED_CUC_COMMIT = ad69400f5446e1c8217af01659c7c10ab00c015b`. This same full commit is used by the reviewed CUC index, Context-Fabric module, Appendix concordance, and reviewed feature-module workflows, and described in `README.md` and `docs/releases/v0.3.0.md`.
- `.github/workflows/test-real-burns-source.yml` instead checks out CUC at `0408967b1808c1f22c69e299d302b1e7b5e26354`. `scripts/check_agora_burns_parent_binding.py::CUC_RELEASE` requires and attests that older SHA as trusted parent binding/receipt. `tests/test_agora_parent_manifest.py` freezes its former literal in CI verification.
- Actual GitHub compare, `DT-UCPH/cuc`, `0408967...ad69400`: exactly four later commits, only `README.md` and `images/caccht-logo.png` changed. No tracked `tf/0.2.8` file changed. Thus the mismatch is *revision identity* and auditability, not observed corpus drift; do not weaken fingerprint matching.

## Release and data boundaries

GitHub PR #122 is already merged to master; release `v0.3.0` is not yet published. #16 requires the exact released commit to have reproducible real-source and parent-contract evidence. Modify only the checkout pin/attested revision and associated synthetic contract tests. Do not include licensed Workbooks or generated artifacts, change lexer alignment, create TF nodes, or weaken source/CUC protections.

## RED criterion

A regression asserting Agora acceptance checks out and attests precisely `REVIEWED_CUC_COMMIT` must fail before implementation. Keep failing test in a separate commit. Validate via the actual GitHub Actions test job before repairing it.
