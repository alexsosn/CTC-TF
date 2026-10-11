# #55 Research: publishing through output-root and ancestor symlinks

## Current code and risk

Two supported CUC-attached module writers exist: primary feature-only `write_feature_module` publishes into an absent directory using a no-replace atomic directory rename, while explicit compatibility `write_burns_module` can transactionally replace a verified six-file module-v1 directory (see stacked #62). Both create stage/output paths relative to the given output parent.

The feature-only writer checks only `output.is_symlink()` and the primary CLI rejects source/CUC overlap with `resolve()`; however, if `--output` has a **symlinked parent directory**, staging and publication can be redirected to a location outside the visually supplied path. The module-v1 writer historically uses `Path.is_dir()` on its output root and would follow a symlink into an existing recognized module, allowing replacement through an alias. Both must refuse symlinked paths.

## Policy proposal and boundary

For either writer, reject **any existing symlink component in the path supplied for output**, including:
- output root (directory symlink or dangling symlink);
- any existing parent component, including direct parent, no matter whether the final output root exists;
- any symlink component added to the path while Fabric saves, before publication.
The common check lives in `publication.py`; call before creating directories/Fabric staging, after preparing parent directories, and directly before destructive/publication moves. The check must avoid `Path.resolve()` because that would mask the alias, and should inspect the path as spelled (including `.. ` segments).

**Caveats:** This is a cooperative filesystem-safety policy; it does **not** prove race-free publication against an adversary that swaps directories between checks and OS operations, and Windows reparse-point/junction handling is not fully covered by a symlink-only probe. Rejecting symlink ancestors may require users to supply a canonical non-symlink path on hosts where system directories are symlinks (e.g. `/tmp` on some macOS systems); explicitly document this tradeoff. Do not follow parent aliases silently.

## Dependencies

The work is prepared as stacked PR on top of #62 to avoid competing edits to `module.py`. Its merge must follow #62 and the frozen `v0.3.0` GitHub Release at commit `4994a45c53a73c09a4939731bc56af585b3ba30a`. It must not change the release candidate, lexical aligner, node universe, six-feature metadata or source parser.

## Review gate

Synthetic symlink fixtures + exact-head Python/real-CUC/consumer CI and independently skeptical review. Reject symlinked owned feature/report files remains the #62 ownership check; source/output overlap remains #56.

## Independently identified stage-root substitution

A separate inspection of the **primary** feature-only writer on the stacked branch finds another symlink trust boundary not covered by its output-path checks: `write_feature_module` creates an internal staging directory, calls injectable `Fabric.save`, then checks **only the staged children**. If the stage directory itself is renamed away and replaced by a directory symlink containing ordinary files with the expected feature names, `stage.iterdir()` and `(stage / REPORT_FILE).write_text` follow that alias. `publish_stage_noreplace` can then publish the *symlink itself* as the feature-module output. The public output can point to foreign data, violating the feature-only producer's self-contained no-symlinks guarantee. Ordinary Text-Fabric is not known to perform this replacement; the test models a compromised/incorrect injected producer.

This is distinct from attacker-controlled output-root symlinks and from expected-file symlinks already reviewed in #118. The source-safe regression must replace the private **stage root** during `Fabric.save` and require rejection before report write or publish, leaving the external directory unchanged. Cleanup must unlink a stage symlink without traversing the target and must never delete foreign data. Concurrency between final checks and OS syscalls remains outside this cooperative validation boundary.

## Second-stage independent review: legacy module-v1 staged root

The stacked branch now includes #118's child-symlink and exclusive staged-report checks, yet `write_burns_module` still trusts the **stage directory root** created by `TemporaryDirectory` after an injectable `Fabric.save` call. A stage-root symlink to a foreign directory containing six ordinary expected `.tf` files makes the child checks pass; `stage / REPORT_FILE` follows the root alias; `Path.replace` then moves the external feature files into public output. This can relocate someone else's data and the temporary-directory cleanup may fail on the alias. The new root check must precede staged child inspection **and** actual publication, and cleanup must unlink aliases without traversing their targets. This is fault-injection protection, not a claim the ordinary Fabric implementation behaves maliciously.
