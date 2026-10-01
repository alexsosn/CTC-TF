# Issue 70 plan: remove the standalone `convert` corpus

Research: `research/issue-70/RESEARCH.md`.

## Phase 1 — preserved RED

Add a focused public-surface contract before deleting production code. It must
fail on the current #69-based branch and require:

1. CLI help excludes `convert`.
2. `cli.main(["convert", ...])` is rejected by argparse as an unknown command
   before source loading/publication.
3. `agora.materializer.json` does not exist.
4. `ugarit_context_parsing.graph`, `.report`, `.writer`, and
   `._semantic_compare` are not importable from the installed package.
5. README no longer advertises the standalone converter or legacy
   single-input materializer manifest.

The RED must not modify production modules, manifest, workflow, or README.

## Phase 2 — GREEN implementation

### CLI/runtime

- remove `sys`, standalone graph/report/writer imports, warning constant,
  `convert` parser, `_run_convert()`, and fallback dispatch;
- leave `module`, `entities`, and `module-v1` behavior unchanged;
- delete:
  - `src/ugarit_context_parsing/graph.py`
  - `src/ugarit_context_parsing/report.py`
  - `src/ugarit_context_parsing/writer.py`
  - `src/ugarit_context_parsing/_semantic_compare.py`.

### Agora/release contracts

- delete `agora.materializer.json`;
- remove the obsolete `agora-contract` workflow job that validates it;
- change release-version tests to require the installed package version and
  absence of the stale manifest;
- rewrite Agora documentation contract around the current `cuc-burns`
  registration and Agora #135 boundary.

### Tests

Delete standalone-only tests:

- `test_materialization.py`
- `test_text_fabric_integration.py`
- `test_pdf_determinism.py`.

Replace mixed files with source-focused equivalents:

- retain identifier/CSV loader tests from `test_tf_materializer.py` in
  `test_csv_source.py`, then delete the old mixed file;
- retain PDF loader/parser-adapter tests from `test_pdf_materialization.py`
  in `test_pdf_source.py`, then delete the old mixed file;
- remove only the `convert`-specific case and warning constant from
  `test_module_cli.py`.

### README

- remove the standalone compatibility paragraph;
- replace the stale legacy-manifest Agora section with current state:
  Agora v1.0.0 / #175 migration complete, `cuc-burns` is the CUC-attached
  registered path, and managed source+parent materialization remains Agora #135;
- keep source extraction, module-v1, native-v2, Appendix and license sections.

## Phase 3 — regression sweep

Search repository contents for residual supported-path references to:

- `convert` as a CLI command;
- `build_tf_data`, `build_conversion_report`, `write_artifact`;
- `conversion-report.json`;
- old materializer IDs;
- `agora.materializer.json`.

Any intentional historical/research mention must not be reachable runtime or
current public documentation.

## Phase 4 — exact-head gates

Require one frozen head with:

- Python 3.10 / 3.12 / 3.13 full suite;
- installed-package smoke proving removed modules are absent;
- reviewed-CUC index contract;
- native-v2 reviewed-CUC + cfabric-mcp consumer smoke;
- Context-Fabric module contract;
- real Workbooks native acceptance;
- Appendix concordance audit.

No Agora manifest validator job remains because the repository no longer owns a
legacy materializer manifest.

## Phase 5 — logically independent adversarial review

Review from a fresh consumer perspective:

- can any public CLI/runtime entry still build the row-slot corpus?
- did deletion accidentally remove CSV/PDF source loading needed by module
  paths?
- does module-v1 still work and remain distinct from removed standalone
  `convert`?
- do README/release tests make truthful Agora claims?
- are dead standalone modules actually absent from the installed package?
- did deleting the old Agora job accidentally weaken unrelated provenance or
  consumer CI?

Any material finding gets a review-derived RED before correction.
