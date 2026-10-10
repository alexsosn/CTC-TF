# #66 Research

The live CLI has two supported commands: default `module` uses `write_feature_module`, explicit `module-v1` uses `write_burns_module`. Both writers intentionally raise `ValueError` for unsafe publication state; the CLI currently propagates those as tracebacks. `False` from Fabric already maps to specific `SystemExit` messages. The deprecated standalone `convert`/`write_artifact` path mentioned in the issue no longer exists, so do not reintroduce it.

Only catch `ValueError` at the exact writer invocation; do not catch errors in source loading, normalization, indexing, alignment, module/report construction, or arbitrary `OSError` from publication (unexpected filesystem faults may require debugging). Labels: `module publication failed:` and `legacy publication failed:`. Preserve existing `False` diagnostics. This is a post-v0.3.0 draft, not eligible for merge until frozen GitHub Release at `4994a45c53a73c09a4939731bc56af585b3ba30a`.
