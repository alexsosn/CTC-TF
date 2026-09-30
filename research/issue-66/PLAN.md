# Issue 66 plan: concise CLI publication diagnostics

Research: `research/issue-66/RESEARCH.md`.

## Phase 1 — preserved RED

Add focused CLI tests only; production remains unchanged.

Required cases:

1. Module writer raises `ValueError("unsafe output")` → `main()` must raise `SystemExit("module publication failed: unsafe output")`.
2. Module writer raises representative `RuntimeError` and `OSError` → same module publication prefix.
3. Legacy writer raises `ValueError("unsafe output")` → `SystemExit("legacy publication failed: unsafe output")`.
4. Legacy representative `RuntimeError` / `OSError` use the same legacy prefix.
5. Module writer returning `False` preserves exactly `Text-Fabric refused the generated Burns module`.
6. Legacy writer returning `False` preserves exactly `Text-Fabric refused the generated dataset`.
7. A `ValueError` injected into `align_burns_source()` is not converted to a publication diagnostic and escapes as `ValueError`.
8. A successful module and successful legacy command retain existing return/output behavior.

Expected RED: writer exceptions currently escape as their original types; false/success/pre-writer behavior already passes.

Use existing test doubles/source fixtures where practical. Keep tests at the public `main()` boundary, not private helper-only tests.

## Phase 2 — GREEN

Change `src/ugarit_context_parsing/cli.py` only:

- define one internal tuple/alias for expected publication exception categories if that improves readability, or inline the explicit tuple;
- wrap only `write_burns_module(...)` in `try/except (ValueError, RuntimeError, OSError)` and convert to `SystemExit(f"module publication failed: {exc}")`;
- wrap only `write_artifact(...)` likewise with `legacy publication failed:`;
- leave existing `False` handling outside/after the exception wrapper so its text is unchanged;
- do not broaden exception handling around alignment, graph/module building, source loading, normalization, or CUC validation;
- do not change CLI arguments, deprecation warning, package version, manifest, writer APIs, or data semantics.

## Phase 3 — exact-head gates

Because the public module CLI changes, require on one frozen final head:

- Python 3.10 / 3.12 / 3.13 + installed-package smoke;
- Agora contract;
- generic Context-Fabric contract;
- reviewed-CUC exact integration;
- real reviewed-CUC + Burns module through cfabric-mcp.

## Phase 4 — logically independent adversarial review

Challenge from scratch:

- whether the catch is genuinely limited to the writer call;
- whether broad `Exception`/`BaseException` handling accidentally hides programming defects;
- whether `KeyboardInterrupt`/`SystemExit` remain untouched;
- whether pre-writer `ValueError` still escapes;
- whether false-return diagnostics remain byte-for-byte unchanged;
- whether writer `OSError`/`RuntimeError` are actionable without a traceback;
- whether the legacy deprecation warning still appears before a legacy publication failure;
- whether any successful output or CLI syntax changes.

Any material finding gets a review-derived RED before correction.

## Phase 5 — merge ordering

Keep draft/unmerged until GitHub Release `v0.3.0` exists at exact commit `4994a45c53a73c09a4939731bc56af585b3ba30a`.

This branch is stacked on reviewed #56. After release, land #56 first, refresh/retest this branch if necessary, then merge #66 with expected-head protection.

## Phase 6 — mandatory native-v2 reconciliation before merge

PR #69 changes the eventual public routing after this plan was first executed.
Once the frozen `v0.3.0` release exists and post-release ordering is selected:

1. Rebase/refresh against the native-v2 command topology.
2. Add/adjust RED contracts so `module`/native-v2 writer exceptions become
   concise publication diagnostics and `module-v1` remains explicitly covered.
3. Keep `convert` behavior and all pre-publication escape tests unchanged.
4. Apply the same narrow writer-call GREEN; do not catch construction/alignment
   failures.
5. Rerun Python 3.10/3.12/3.13, installed-package, Agora, generic
   Context-Fabric, reviewed-CUC, and native Burns/cfabric-mcp gates.
6. Conduct a new logically independent adversarial review on that rebased exact
   head before merge.

The already-preserved v1 RED/GREEN history remains evidence for the boundary
design but does not substitute for this routing reconciliation.
