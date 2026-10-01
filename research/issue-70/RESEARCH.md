# Issue 70 research: remove the standalone `convert` corpus path

## Current product boundary

Research is performed against finalized native-v2 PR #69 head
`7dbf8ad00143d72619e346a987d6dd7969b08680`, not frozen pre-v2 `master`.

The supported CUC-attached paths on that head are:

- `module` / `entities`: native-v2 Burns entity extension over reviewed CUC;
- `module-v1`: explicit compatibility feature module over reviewed CUC.

Issue #70 does **not** remove `module-v1`.

The obsolete path is the independent row-slot corpus behind `convert`. It creates
its own `record` slots and `worksheet/section/entry` nodes, so it is a
different corpus architecture rather than a compatibility encoding of the CUC
module.

## External Agora status

Agora v1.0.0 is published and Agora PR #175 is merged. Agora no longer
registers or CI-smokes the two old `ugarit-context-parsing convert`
materializers. The Burns product is registered as `cuc-burns`, a
CUC-attached feature-module/local-module composition. Managed execution from
user-local Burns source plus an Agora-managed reviewed-CUC parent remains
separately tracked in Agora #135.

Therefore the repository-local `agora.materializer.json` is stale product
metadata: both entries still invoke `convert` and advertise a standalone
Text-Fabric output that Agora no longer supports.

## Standalone runtime inventory

The row-slot path is isolated behind these package modules:

- `src/ugarit_context_parsing/graph.py`
  - `TFData`
  - `build_tf_data()`
  - creates standalone `record` slots and worksheet/section/entry hierarchy.
- `src/ugarit_context_parsing/report.py`
  - `build_conversion_report()`
  - creates `conversion-report.json` metadata for the standalone corpus.
- `src/ugarit_context_parsing/writer.py`
  - `write_artifact()`
  - publishes the independent TF warp and conversion report.
- `src/ugarit_context_parsing/_semantic_compare.py`
  - standalone-artifact semantic comparison helper used by legacy determinism
    tests.

On #69, `cli.py` imports those modules only for `_run_convert()`.
The native-v2 and module-v1 paths use the source loaders, normalization,
alignment, reviewed-CUC index and their own module/entity writers.

## Tests: delete versus preserve

Standalone-only coverage can be deleted:

- `tests/test_materialization.py`;
- `tests/test_text_fabric_integration.py`;
- `tests/test_pdf_determinism.py`;
- graph/report/writer/manifest portions of `tests/test_tf_materializer.py`;
- graph/convert portions of `tests/test_pdf_materialization.py`;
- the legacy-convert routing assertion in `tests/test_module_cli.py`.

Useful shared coverage must survive:

- KTU identifier normalization;
- recursive CSV source discovery, schema validation, row preservation,
  appendix exclusion and symlink rejection;
- PDF source discovery/order, symlink rejection and public parser adapter.

Rather than leave those tests in files named after the deleted materializer,
move them to source-focused tests (`test_csv_source.py`,
`test_pdf_source.py`).

## CI / release contracts

`.github/workflows/test.yml` still contains an `agora-contract` job that
checks out an old Agora validator and requires the stale local manifest plus
the two removed materializer IDs. Once the manifest is deleted, that job is no
longer a valid product contract and should be removed.

`tests/test_release_version.py` currently requires the manifest/version/IDs.
After #70 it should keep the installed-package version assertion and require
that no repository-local `agora.materializer.json` remains.

`tests/test_agora_status_documentation.py` currently requires README wording
about legacy single-input materializers. It should instead require truthful
current architecture: Agora v1.0.0 / #175 migration completed, `cuc-burns`
registered as the CUC-attached path, and Agora #135 still owns managed
materializer-produced parent orchestration.

## Public documentation

README currently says:

- the standalone converter remains available under `convert`;
- the local Agora manifest intentionally declares the old single-input
  materializers.

Both become false after #70 and must be removed/replaced. Source extraction,
native-v2 usage, module-v1 compatibility, Appendix scope and licensing remain.

## Removal safety

Deleting the standalone path must not remove or weaken:

- `source.py` / `pdf_source.py`;
- `identifiers.py`;
- source parser scripts;
- annotation normalization/alignment;
- reviewed CUC compatibility checks;
- native-v2 entity publication;
- explicit `module-v1` CUC feature-module compatibility.

No migration shim or hidden alias from `convert` should remain. After the
change, argparse must reject `convert` as an unknown command.

## TDD conclusion

A focused RED should assert the *absence* of the obsolete public surface before
production deletion:

1. help does not list `convert`;
2. invoking `convert` exits as an argparse unknown command;
3. `agora.materializer.json` is absent;
4. standalone runtime modules are not importable;
5. README contains no supported standalone-converter instructions.

That RED will fail against #69 without modifying production. GREEN then removes
the isolated implementation and legacy contracts while preserving source and
CUC-module tests.

## CI amendment: old generic Context-Fabric contract is standalone-only

A later dependency sweep found that `scripts/check_context_fabric_contract.py`
still invokes `convert`, asserts the row-slot `record/worksheet/section/entry`
corpus, and is executed by the generic `context-fabric-contract` job in
`.github/workflows/test.yml`. This is not a shared consumer check and must be
removed with the standalone corpus.

Consumer coverage is not lost: #69 already has separate permanent workflows
for the CUC-attached feature module (`test-context-fabric-burns-module.yml`)
and native entity extension (`test-reviewed-cuc-burns-entities.yml`), both
against pinned Context-Fabric/cfabric-mcp and reviewed CUC. The generic
standalone job should therefore be deleted rather than rewritten to duplicate
those contracts.
