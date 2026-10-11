# #55 Plan: fail closed for symlinked output roots and ancestors

1. RED tests for both live writers with symlinked output root and symlinked parent, checking that no Fabric is constructed and all target directory contents remain byte-identical. Include dangling symlink output root, and feature-only output absent under an alias parent. Add a stage-time symlink parent injection negative case if viable in a deterministic fixture.
2. GREEN add one `reject_symlinked_output_path()` helper to `publication.py`, scanning path components as spelled without resolving them. Call at both writer preflights and just before their publication actions; preserve stage cleanup and rollback, no owned-file removal by prefix.
3. Contract tests retain legal paths, including output in a newly created honest parent directory, and empty/new output for primary feature writer.
4. Run exact-head Python matrix and pinned real Workbooks, reviewed CUC and Context-Fabric consumer gates.
5. Logically independent adversarial review should challenge `Path.resolve` alias masking, output root TOCTOU, symlinked ancestor components, symlinked report/feature handling, and host-specific filesystem assumptions. No merge before #62 and release gate.

## Independent adversarial sub-loop: staged root replacement

1. **RED:** add a synthetic feature-only Fabric save fixture that replaces its staging directory with a symlink to a foreign directory holding exactly the expected feature file names, no report. Assert the writer refuses the stage before report or publication, keeps the foreign directory and its bytes unchanged, and creates no public output. Preserve this as a separate commit and confirm a real Python CI failure.
2. **GREEN:** check stage-root type/non-symlink just after Fabric.save and again directly before publish. Harden final cleanup to unlink any stage-root symlink, rather than `shutil.rmtree` through a link. Retain existing child inventory / no-clobber validation. Use no generic `Path.resolve` that would hide aliases.
3. Rerun exact-head Python 3.10/3.12/3.13 and real-source/Context-Fabric acceptance, review independently against real code and synthetic fault injection. Keep stacked PR draft until #118 and the v0.3.0 release are complete.
