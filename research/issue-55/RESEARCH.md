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
