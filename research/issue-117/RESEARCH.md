# #117 Research: Agora parent-bound CUC Burns materializer

The current Agora `registry/schema/materializer-plugin.schema.json` requires `schema_version=1`, plugin identity/version and a materializer with user-local acquisition, directory input, network-denied `python-module` execution, and output. Parent-aware contracts support `parent_input.resource`, `parent_versions`, `required_paths`, an explicit `{parent}` argument and `output.composition.kind=feature-module`. The Agora `tests/test_materializer_parent_input.py` tests validate consistency between parent and output metadata.

The live Burns producer is `ugarit_context_parsing.cli module`, **not** the deleted standalone `convert`. It accepts local CSV Workbooks, `--cuc` reviewed parent, and `--output` absent output; the TF output is feature-only with report `burns-feature-module-report.json`, no `otype.tf`, `oslots.tf` or `otext.tf`. The Python package version is `0.3.0`. The manifest must declare a *local-only* source, no automatic Burns acquisition, and `allow_symlinks=false`. Agora registry registration and executable integration need coordination with Agora #135 and the frozen producer release. No Burns data is committed.

The pinned CUC resource in Agora is expected to be 0.2.8, with `otype.tf`, `oslots.tf`, `otext.tf`. Do not conflate a source Git revision with the immutable Text-Fabric data-tree identity; full source/parent integration must verify exact tree compatibility separately. The manifest must not claim it alone proves that integration.

## Gate
No release/merge before GitHub Release `v0.3.0` points to frozen commit `4994a45c53a73c09a4939731bc56af585b3ba30a`. A post-release manifest PR remains draft until reviewed producer version/pin and Agora registration are aligned.

## Verified parent resolver behavior

Agora `scripts/agora_materialize.py::_validate_execution_parent` checks required TF files **directly beneath** `ParentBinding.path`, requires trusted `resource_id=cuc`, compatible `version=0.2.8`, immutable 40/64-hex source revision and a nonempty trusted `relative_path`, and rejects symlinked parents and writable overlap before acquiring Burns source. Therefore the orchestrator must bind the actual TF leaf containing `otype.tf/oslots.tf/otext.tf` (often `tf/0.2.8`), **not** the repository root. `materialize` requires the OS sandbox for a parent-bound run, and `validate_output` rejects symlinks and any warp files recursively. A manifest cannot on its own attest the parent trust or resolve the TF leaf; Agora #135 must prove that path selection and pinned tree hash in a real integration run.
