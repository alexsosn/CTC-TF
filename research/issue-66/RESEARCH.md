# Issue 66 research: concise CLI diagnostics for publication failures

## Current CLI boundary

The public CLI already translates several expected user/input failures into concise `SystemExit` messages:

- `SourceValidationError` → `source validation failed: ...`;
- `BurnsNormalizationError` → `Burns normalization failed: ...`;
- `CucCompatibilityError` → `CUC validation failed: ...`;
- source/output overlap → direct `SystemExit`;
- a writer returning false → the existing `Text-Fabric refused ...` message.

But the actual writer call is not guarded. Expected publication rejection therefore escapes as a Python exception/traceback instead of the same CLI style.

This issue is intentionally stacked on reviewed #56 head `26a084f6a59f875811876dca5e5220d4197996ab`, because #56 changes the same `cli.py` and already defines the source/output pre-publication boundary.

## Writer exception inventory

### Feature-module writer

`write_burns_module()` intentionally raises:

- `ValueError` for invalid/unsafe module/report/output state (foreign TF files, wrong inventory, symlinks, invalid report/metadata, invalid output path, etc.);
- `RuntimeError` for Text-Fabric/integration publication failures such as required staged feature inventory being wrong or Text-Fabric not being importable;
- `OSError` subclasses for filesystem failures during staging/report writing/publication/rollback.

It also returns `False` when `Fabric.save()` explicitly refuses the save. The CLI already maps that false return to `Text-Fabric refused the generated Burns module` and that message should remain unchanged.

### Legacy writer

`write_artifact()` intentionally raises the same broad categories at the publication API boundary:

- `ValueError` for invalid generated graph/report or unsafe output state;
- `RuntimeError` for required Text-Fabric output omissions or missing Text-Fabric runtime;
- `OSError` subclasses for filesystem publication failures.

It returns `False` when `Fabric.save()` refuses the save; the existing CLI maps that to `Text-Fabric refused the generated dataset`.

## Selected boundary

Catch exactly `(ValueError, RuntimeError, OSError)` **only around the writer call**.

Do not wrap:

- normalization;
- CUC indexing;
- alignment;
- module construction;
- module report construction;
- graph/report construction.

That means a `ValueError` from `align_burns_source()` or `build_burns_module()` remains an uncaught programming/data-model error and retains its traceback for debugging. The CLI does not use a broad `except Exception`.

Selected messages:

- module writer exception → `SystemExit("module publication failed: <writer message>")`;
- legacy writer exception → `SystemExit("legacy publication failed: <writer message>")`.

The existing false-return messages remain byte-for-byte unchanged.

## Why no new exception hierarchy in this ticket

A dedicated `PublicationError` hierarchy could be useful eventually, but introducing it now would require touching both writer implementations and every reviewed post-release output-safety branch (#54/#55/#62), creating unnecessary merge conflicts and widening a CLI ergonomics change.

The writer call boundary is already an API seam. An explicit tuple of expected standard exception categories at that narrow boundary is sufficient without masking earlier pipeline defects.

## `SystemExit` behavior

Tests should call `main()` and assert the `SystemExit` value directly. The console-script wrapper exits nonzero with that string; `SystemExit` is the CLI's existing failure mechanism, so no new logging framework or exception printer is needed.

The test contract should also prove that writer exceptions never escape as their original type, while an injected pre-writer alignment/build `ValueError` still does.

## Merge ordering

This is post-v0.3.0 ergonomics work. Keep the branch reviewed but unmerged until GitHub Release `v0.3.0` exists at exact frozen release commit `4994a45c53a73c09a4939731bc56af585b3ba30a`.

Because this branch is stacked on #56, post-release landing order is #56 first, then #66. Writer-safety changes #60/#61/#65 are independent of this CLI boundary and can then surface their rejection through the same concise diagnostics.

## Native-v2 reconciliation discovered after the original GREEN

PR #69 subsequently changes the post-release public command topology: `module`
becomes the native-v2 entity publisher, while the v1 feature writer moves behind
explicit `module-v1`. The current #66 implementation remains a valid,
reviewable patch on its frozen v1 stack, but it must not be mechanically merged
after #69 while still wrapping only `write_burns_module()`.

Before eventual landing after the frozen first release, refresh this branch
against the chosen post-release integration order and preserve the same narrow
boundary for all public writers:

- native `module` / `entities`: translate only expected
  `write_entity_artifact()` publication errors;
- explicit `module-v1`: translate only expected `write_burns_module()`
  publication errors;
- `convert`: retain the existing `write_artifact()` legacy diagnostic;
- normalization, CUC verification, alignment and artifact construction remain
  outside publication exception handling.

That rebase/reconciliation requires fresh RED/GREEN where routing differs and a
new exact-head reviewed-CUC/cfabric smoke. The current branch must therefore be
treated as pre-rebase reviewed evidence, not as a future conflict-resolution
recipe.
