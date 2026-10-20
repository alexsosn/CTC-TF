# #133 — Plan: precise post-release user documentation

1. Freeze research verifying real upstream released tag, immutable registry pin, explicit approval, stable-only passive release tracking, separate read-only CUC and native feature-module output.
2. Preserve test-first RED in `tests/test_agora_status_documentation.py`: require currently reviewed released SHA, explicit `github-releases` + `stable` + `tag_prefix: v`; reject previous `f58b162...` and `release tracking disabled` wording in the current-status section. Keep licensing/no-implicit-source-install and CLI assertions unchanged. RED must precede README change.
3. GREEN only README Agora-status paragraph; preserve native quickstart and explanation of approved managed path. Explain `release_tracking` is review-only; changing registry does not auto-upgrade existing installations.
4. Run exact-head Python matrix and README/Bash syntax contracts; independent adversarial review checks diff, upstream live registry, real prior 45-Workbook E2E and no stronger user-facing promises. This prose change does not require duplicating expensive licensed-source E2E already passed on exact upstream producer.
5. Merge with expected HEAD SHA after all gates; close #133. No version bump, generated Burns datasets, new TF nodes or changed CUC source.

## Adversarial CI regression after first GREEN (2026-10-20)

Full exact-head run `39388759482` failed under Python 3.10/3.12/3.13 for two **preexisting** documentation contracts: `test_unfinished_general_orchestration_not_conflated_with_available_cli` requires contiguous `Agora #135` text; `test_converter_source_and_agora_boundaries_remain_explicit` requires a reader-visible phrase `release tracking`. The first GREEN line-wrapped the former and represented the latter solely as literal code field `release_tracking`. Correct the README prose rather than weakening these valuable legacy contracts; rerun exact-head full matrix. This preserves the initial witnessed RED (run `39388701356`) for the intended new assertions and the separate post-GREEN regression as adversarial test evidence.
