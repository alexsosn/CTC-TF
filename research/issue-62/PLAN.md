# #62 Plan: fail-closed module-v1 publication

1. Research existing `write_burns_module` and `_publish` semantics, the exact six expected features, report identity, and existing rollback tests. Freeze the primary `module` product path.
2. Preserve causal **RED tests**:
   - existing `burns_custom.tf` (unknown prefixed regular file) survives and causes error **before Fabric construction**;
   - any report-only/partial/invalid-schema output fails with original bytes unchanged;
   - a complete prior module with exact six files and valid marker remains replaceable;
   - failure in staged publication restores every byte from a complete prior module;
   - an unknown prefixed file introduced **during** Fabric.save must be detected before publication and preserved;
   - unrelated note files survive a valid prior-output replacement.
   Replace old tests that incorrectly expect the destructive wildcard cleanup or invalid ownership to be treated as a valid prior module.
3. **GREEN**: write a small shared output-ownership validator, called by preflight and by `_publish` after staging. Back up only exact reviewed six filenames and report. No new parser, feature, node, or lexical alignment changes.
4. Run full supported Python matrix, pinned CUC Workbooks and downstream contracts on an exact commit. Do not claim CI tests passed until workflows report completed/success.
5. Conduct exact-head logically independent adversarial review: attack forged/incomplete marker, time-of-check-to-time-of-use insertion, foreign-file preservation, rollback under injected replace failure, and symlinks (separate follow-up #55). Maintain draft and **do not merge until GitHub Release v0.3.0 points to the required frozen commit**.

## Adversarial review-derived refinement: staged symlink laundering

An independent source audit found that `write_burns_module` currently builds its staged feature inventory with `path.is_file()`, which follows links. An expected `burns_*.tf` name pointing to an external file is accepted as one of the six features, then `Path.replace` moves the symlink into public output. This bypasses the existing preflight restriction on prior output symlinks and can leave the published legacy module referencing unrelated local data. Treat this as a distinct publication safety test within #62, not as evidence that the ordinary Text-Fabric writer creates symlinks.

- **RED:** synthetic Fabric factory creates all six expected stage names but makes one an external-file symlink. Expect fail-closed *before live module backup/replacement*, with the previous complete module and external sentinel bytes unchanged. Preserve the test as an isolated commit and observe actual failing CI.
- **GREEN:** reject every stage entry that is a symlink or non-regular feature file even if its name appears in the reviewed six-name inventory. Do not follow any symlink; do not weaken the exact inventory check or change CUC nodes.
- **Gates:** rerun exact-head Python matrix and all source/consumer workflows, independent final adversarial review, keep #118 draft until published v0.3.0.

### Second independently derived variant: staged report symlink

The writer calls `(stage / REPORT_FILE).write_text(...)` without verifying that an injected staged report path is absent. A synthetic Fabric can populate `burns-module-report.json` as a symlink to an outside sentinel; Python `write_text` follows it and overwrites unrelated data. Preserve an additional review-derived RED proving the existing writer mutates this foreign sentinel, then fail closed **before opening** a non-absent report path. Existing report creation must remain exclusive/no-follow; stage names should be inspected as ordinary files before any live publication. This extends the same #62 staged-publishing trust boundary, not its lexical coverage.
