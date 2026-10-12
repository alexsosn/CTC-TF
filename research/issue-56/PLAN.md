# #56 Plan: reuse production overlap guard on module-v1

1. Research existing default `module` symmetric overlap check and explicit `module-v1` route, plus CLI mocks/source loader root.
2. RED tests demonstrate source-root, nested output, ancestor output, CUC overlap, and symlink alias overlap are not all rejected by current v1, while nonoverlapping paths remain accepted. Preserve file contents and mock normalization/index to ensure rejection is early.
3. GREEN minimal patch: invoke existing `_reject_module_overlap(source.root, args.cuc, args.output)` in `_run_module`, after the validated source loader and before normalization; generalize message if needed to refer to both module formats. Repair old fake-source fixtures to provide `root`.
4. Run exact-head Python matrix, reviewed CUC contracts, pinned real Workbooks, Context-Fabric. Keep output and CUC node semantics unchanged.
5. Independently adversarial review exact head: input/output ancestor symmetry, alias resolution, no CUC index call on rejected paths, legitimate v1 functionality, and no overclaim about filesystem race guarantees. Hold merge until frozen v0.3.0 release exists at required SHA.
