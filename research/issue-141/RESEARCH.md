# #141 Research: safe destinations for both audit private report options

## Verified code behavior on merged #140

The general `scripts/audit_burns_alignment.py::main` accepts both `--report` (the full Burns alignment report) and `--private-out-of-order` (the narrowly scoped case review). Both eventually call `_write_private_report`, which creates an owner-only 0600 staged file, fsyncs, then atomically `os.replace`s the caller-supplied output destination.

Only `--private-out-of-order` currently rejects paths resolved inside `ROOT` checkout, local Workbooks root, and pinned CUC TF directory. `--report` does not. An explicit `--report /CUC/tf/0.2.8/otype.tf` would overwrite that important upstream TF input, independent of any primary Burns TF module publication safeguards. A symlinked alias to such a destination also bypasses naïve string tests. This is a local output-path hazard, not a production TF warp bug.

Two explicit output flags may also resolve to **the same destination**. `main()` writes `--report` first and then `--private-out-of-order`, thus silently losing the first report. A small path-identity guard should reject this combination before acquiring/parsing data. All report content remains restricted/local, never pushed to GitHub.

## Bounded design

Run one shared preflight over **each requested private report destination**, after discovering Workbooks path and before parsing source. Resolve paths and reject descendants of checkout, Workbooks or reviewed CUC TF input, including symlink aliases. Reject duplicate resolved destination paths when both flags are present. No changes to `_write_private_report`, serialization, source parsing, public stdout, materializer, lexical matching, or CUC warp. Preserve valid owner-only reports outside protected trees.

## Testing

Actual RED using synthetic local paths must distinguish intended overlap failure from test-harness syntax/errors, confirm absence of overwritten temporary source CUC files, and check valid outputs remain mode 0600 and aggregate stdout contains no source strings. Exact-head green needs Python 3.10/3.12/3.13 plus 45-Workbook reviewed CUC 0.2.8 / Agora Bubblewrap acceptance and an end-user CLI smoke. Independent review must challenge path aliases, output collisions, race caveats and default compatibility.
