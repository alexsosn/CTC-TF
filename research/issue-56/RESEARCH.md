# #56 Research: source/CUC/output overlap in Burns CLI

## Verified present architecture

The **default feature-only** `module` CLI calls `_reject_module_overlap(source.root, args.cuc, args.output)`, which compares resolved paths in both directions and rejects output that is equal to, nested in, or an ancestor of either input tree. Its writer independently requires an absent output path and no CUC warp mutation.

Explicit compatibility `module-v1` routes through `_run_module()` and the older six-feature `write_burns_module()`. On the current code, it does **not** call the shared overlap guard; it loads the full source and then can write into or replace a recognized prior module in a directory that is also the source or reviewed CUC tree. Even with #62's ownership hardening, a user-specified output that overlaps input/source tree should not be considered safe.

## Decision

Apply the existing strict, *symmetric* physical-path-overlap guard to **both** CLI routes, before normalization, CUC indexing, or Fabric publication. This protects user-local Burns source CSV/PDF, CUC reviewed base, and a parent tree containing either, including path aliases resolved through symlinks. Do not modify the general-purpose writer's acceptance of valid prior outputs; its own ownership policy is addressed by #62.

There is no supported need for source and output co-location: documentation already instructs separate directories. This is a CLI policy, not a transformation of source contents, not a new materializer and not a CUC node change.

## Tests and limitations

RED: source-root equality, output nested under source, output ancestor of source, output nested/equal/ancestor of CUC, alias/symlink to source/CUC roots. Rejection must occur before normalization/indexing/Fabric and must leave input bytes untouched. Regression test nonoverlapping explicit v1 CLI calls still route to the existing writer. Source mocks in existing CLI tests must expose their source root, matching the actual `LoadedWorkbookSource.root` contract.

The physical path comparison uses `Path.resolve()` to detect overlap, intentionally unlike #55's symlink-output-policy which scrutinizes the caller's raw path spelling. Neither path check claims race-free protection against malicious concurrent directory swaps.

## Release boundary

Do not merge before frozen v0.3.0 GitHub Release exists at `4994a45c53a73c09a4939731bc56af585b3ba30a`. This feature-free safety patch is prepared on a separate branch from master; it is independent of #118 and stacked #119 and changes only CLI routing/test/docs.
