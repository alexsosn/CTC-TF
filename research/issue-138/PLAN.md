# #138 Plan — research → RED → GREEN → exact-head gates → independent review

1. Research existing CLI and the source-safe aggregate (committed separately as RESEARCH.md), with local PDF-only input semantics and restricted --report behavior.
2. Commit synthetic CLI regression in tests/test_alignment_audit_cli.py as RED before implementation: with patched PDF/CUC **loading only**, actual normalizer/aligner, compare default JSON without flag to opt-in JSON; require one_missing_unique_containment with independent annotation counts; assert source lexemes/KTU/IDs absent and no implicit full report or source fetch.
3. Capture RED from exact test commit in GitHub CI when possible; if concurrency cancels CI, independently verify failure from the pre-GREEN CLI argparse contract, recording the limitation honestly.
4. GREEN only scripts/audit_burns_alignment.py main() argparse and output assembly. Reuse aggregate_multitoken_residual_research; preserve all default keys, stdout structure, --report owner-only semantics and failure behavior. Document exact opt-in PDF-workbooks command in README.
5. Run exact final HEAD Python 3.10/3.12/3.13 and real 45 licensed Workbooks + reviewed CUC 0.2.8 + Agora Bubblewrap acceptance; check unchanged TF warp and source-safe diagnostic class totals. No direct data/code redistribution.
6. Fresh logically independent adversarial review on the actual final diff, tests and CI logs. Challenge flag-off compatibility, accidental report creation, source exposure, wrong path semantics, no-data cases, unreviewed lexical rules and runtime overhead. Fix with separate RED/GREEN if necessary; merge with exact head lease and close issue only after full gates.

Risk control: This is diagnostic CLI exposure, not morphology matching, new corpus architecture, or TF feature schema change.
