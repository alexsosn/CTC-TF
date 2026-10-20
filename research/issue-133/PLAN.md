# #133 — Plan: precise post-release user documentation

1. Freeze research verifying real upstream released tag, immutable registry pin, explicit approval, stable-only passive release tracking, separate read-only CUC and native feature-module output.
2. Preserve test-first RED in `tests/test_agora_status_documentation.py`: require currently reviewed released SHA, explicit `github-releases` + `stable` + `tag_prefix: v`; reject previous `f58b162...` and `release tracking disabled` wording in the current-status section. Keep licensing/no-implicit-source-install and CLI assertions unchanged. RED must precede README change.
3. GREEN only README Agora-status paragraph; preserve native quickstart and explanation of approved managed path. Explain `release_tracking` is review-only; changing registry does not auto-upgrade existing installations.
4. Run exact-head Python matrix and README/Bash syntax contracts; independent adversarial review checks diff, upstream live registry, real prior 45-Workbook E2E and no stronger user-facing promises. This prose change does not require duplicating expensive licensed-source E2E already passed on exact upstream producer.
5. Merge with expected HEAD SHA after all gates; close #133. No version bump, generated Burns datasets, new TF nodes or changed CUC source.
