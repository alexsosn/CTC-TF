# Issue #70 plan: remove standalone `convert`

## Acceptance target

After this change the supported package has no command, manifest, implementation path, CI contract, or public documentation that creates/advertises the standalone Burns row-slot corpus. CSV/PDF source parsing and CUC-attached `module-v1` / native-v2 paths remain intact.

## TDD sequence

1. Preserve RED tests requiring:
   - `convert` absent from CLI help;
   - `convert` rejected as an invalid command;
   - obsolete `agora.materializer.json` absent.
2. Remove CLI parser/dispatch/imports and standalone warning.
3. Delete the obsolete manifest.
4. Remove standalone-only graph/report/writer code.
5. Split tests so shared CSV/PDF loader and identifier invariants remain covered while standalone graph/publication assertions disappear.
6. Remove standalone-only deterministic/integration helpers and old Context-Fabric row-slot consumer job.
7. Update current README, Agora-status docs and unreleased v0.3.0 notes.
8. Adversarially scan active source/tests/docs/workflows for:
   - old materializer IDs;
   - `conversion-report.json`;
   - standalone `convert` invocation;
   - row-slot compatibility promises.
   Historical research notes are not rewritten.
9. Run the full Python matrix plus CUC module/native consumer workflows on an exact stacked head.
10. Perform a logically independent adversarial review. Keep #71 draft/stacked until #69 is resolved.

## Non-goals

- removing `module-v1`;
- changing Burns alignment semantics;
- implementing Agora #135 parent-resource execution;
- changing CUC compatibility identity;
- rewriting historical research records.
