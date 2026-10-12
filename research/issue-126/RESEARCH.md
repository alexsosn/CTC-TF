# Issue #126 — research: exclusive report write in primary Burns feature module

## Current code

The primary `write_feature_module` in `src/ugarit_context_parsing/feature_module.py` uses an absent-destination contract, `tempfile.mkdtemp` (private stage), a genuine `Fabric.save` into stage, and an `entries = tuple(stage.iterdir())` snapshot. It rejects unexpected features, directories, and symlinks in that **snapshot** before writing `burns-feature-module-report.json`. It then calls `(stage / REPORT_FILE).write_text(report_text, encoding="utf-8")`, which follows symlinks. `publish_stage_noreplace` does not permit overwriting the final output path.

An independent code-path challenge distinct from legacy `module-v1` #118: if a same-UID concurrent actor can create `stage/REPORT_FILE` **after** snapshot enumeration, the subsequent plain `write_text` can modify a foreign local target *before* the no-replace publication step. This is not an ordinary source-file exploit: stage `mkdtemp` is mode 0700; adversarial concurrent access by a same-UID process or injected writer is assumed. Normal Text-Fabric saves do not introduce this link. A narrowly deterministic synthetic regression can simulate the window by making stage `Path.iterdir` return its prior contents and create the symlink before returning the list to the writer.

Legacy PR #118 separately introduced exclusive report creation for the `module-v1` writer. The primary writer already checks all stage entry types, so the only uncovered gap is the snapshot-to-report-write race. Do not change feature inventory, source normalization/alignment, output node model, or CUC fingerprint policy.

## Acceptance / limits

Reject an existing or symlinked report path without following it, using exclusive creation. Prove a synthetic foreign sentinel is unchanged on refusal; output remains absent. Keep successful report bytes, deterministic ordering, exact emitted `.tf` feature inventory and real CUC node universe unchanged. Audit under Python 3.10/3.12/3.13, real Workbooks, pinned CUC, Context-Fabric and Agora Bubblewrap CI, and logically independent final adversarial review.

The current GitHub tag and Release `v0.3.0` are absent. This hardening is **post-release** and must remain draft/unmerged until issue #16 is completed and the subsequent release/version policy is settled. No Burns-licensed data in commit/test fixtures.
