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
