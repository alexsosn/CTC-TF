# #52 Plan: docs-only TDD

## RED

Add a lightweight standard-library test that extracts the named local-CUC quickstart bash block and requires:
- reviewed upstream CUC URL and immutable full SHA;
- explicit shallow fetch and detached checkout;
- `tf/0.2.8` derived from the actual checkout;
- real `ugarit-context-parsing module` CLI with CSV input, `--cuc`, and absent `--output`;
- `bash -n` valid syntax;
- explicit no implicit CUC download by materializer, Burns CSV input remains user-local;
- no assertion that Agora autonomously materializes a parent-managed CUC module.

This must fail against the existing README.

## GREEN

Add the smallest standalone reproducible copy-paste sequence to README. Do not change code, pinning, schema or CLI behavior.

## Test

Run the docs test and the relevant Python matrix on exact PR head. Since user-run environment has no network in CI tests, do *not* automatically clone CUC from the test; validate the command syntax and compare the immutable constants with production. Optionally test the Git URL and commit via connected upstream GitHub metadata, separately.

## Review and release gate

Logically-independent adversarial review should attack fake network guarantees, wrong relative path, shell variable quoting, accidental download/redistribution claims, and release status. Do not merge prior to the verified v0.3.0 release at exact frozen commit.
