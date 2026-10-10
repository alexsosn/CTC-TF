# #62 Research: ownership of existing module-v1 Burns TF outputs

## Live risk confirmed

The primary `module` CLI is a feature-only CUC overlay and publishes **only to an absent output directory**. The explicit `module-v1` compatibility CLI still invokes `write_burns_module()` in `src/ugarit_context_parsing/module.py`. That writer currently treats **every** pre-existing `burns_*.tf` as owned: preflight exempts the entire prefix and `_publish()` backs up/removes all files matching the prefix. `burns_custom.tf` is therefore destructively deleted if it shares the output directory.

The compatibility feature inventory is explicitly fixed to six named files (`FEATURES` / `_EXPECTED_TF_FILES`) and the identity marker is `burns-module-report.json` with `MODULE_REPORT_SCHEMA`, `feature_inventory` and exact reviewed `cuc_compatibility`. A mere filename prefix cannot authorize deletion.

## Decision

- Empty or absent output directories are safe. Non-TF notes may coexist and are preserved.
- An existing Burns-compatible output must have **exactly the six reviewed TF filenames**, no other `*.tf` (whether or not prefixed), and a **regular** report whose schema, six-feature inventory, and reviewed CUC identity agree with the current published module contract. A missing/invalid report, partial set, extra TF or symlinked marker is insufficient evidence of ownership.
- Only the exact six reviewed feature files and recognized report may be replaced. No wildcard deletion; never delete `burns_custom.tf` or similar unknown files.
- Validate the live output both **before creating Fabric** and again **after staging, immediately before backup/replacement**, so an unknown file injected during Fabric.save cannot bypass preflight. Restrict the destructive move list independently of validation. Keep rollback transactional.
- Do not infer file content integrity cryptographically from this report: the v1 marker includes no per-file digest. Treat schema/inventory/CUC identity as cooperative ownership metadata, not proof against a malicious forged marker; do not claim stronger guarantees.
- Keep output symlink policy of #55 and CLI source/output overlap policy of #56 separate; this ticket only addresses unknown pre-existing TF files and incomplete ownership.

## Research caveat and release gate

Legacy tests currently assume replacement of `{"old":true}` partial outputs and deletion of stale unknown prefixed files. Those are **unsafe historical assumptions**; update them to use a complete previous synthetic module and assert explicit fail-closed behavior on ambiguous/incomplete outputs instead. New RED should fail on the old writer before GREEN.

This is **post-v0.3.0** work. The required frozen release `v0.3.0` at `4994a45c53a73c09a4939731bc56af585b3ba30a` is not published yet (GitHub release endpoint returned 404). Work may be prepared on a separate draft PR but **must not merge** until the release gate, exact-head full CI and independent adversarial review are satisfied.
