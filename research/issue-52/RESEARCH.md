# #52 Research: reproducible local reviewed-CUC quickstart

## Grounded contract

`src/ugarit_context_parsing/cuc_index.py` pins the **exact** reviewed CUC repository `DT-UCPH/cuc`, full commit `ad69400f5446e1c8217af01659c7c10ab00c015b`, version `0.2.8` and six required-file fingerprints. GitHub confirms the commit exists in upstream. `pyproject.toml` exposes `ugarit-context-parsing`; the CLI accepts `module SOURCE --input-format csv --cuc PATH --output ABSENT_PATH`.

The Burns source is separate: local CSVs come from the parser/source deposit; CUC is not downloaded by the materializer. The module owns no warp. `module` refuses an existing output directory and refuses overlap with the source/CUC roots.

## Documentation decision

Offer a short shell transcript explicitly obtaining CUC at the immutable SHA using an intentionally shallow, detached fetch; use distinct local paths:
- clone/check out this **software** repository in `$BURNS_REPO` (command runs from repository checkout);
- `$CUC_DIR` as fresh sibling checkout and `$CUC_TF` as `$CUC_DIR/tf/0.2.8`;
- `$BURNS_CSV` for already extracted licensed CSV input;
- `$BURNS_MODULE` as absent output.

Command grammar must match real CLI and must not imply `module` downloads CUC or Burns. The user supplies their own source data, preserving Burns's CC BY-NC-ND restrictions. The downstream base/module loading order is unchanged.

Git itself fetches CUC explicitly as a user step. The module remains offline; this distinction is important.

## Release dependency

Issue #52 is explicitly **post-v0.3.0**. Do not merge documentation or assert a release has been published until the frozen GitHub Release v0.3.0 is independently verified at commit `4994a45c53a73c09a4939731bc56af585b3ba30a`. Research/PR work may be prepared beforehand; release-gated merge may not.
