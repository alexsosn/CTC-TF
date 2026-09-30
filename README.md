# CTC-TF / ugarit-context-parsing

Local extraction and Text-Fabric materialization of Duncan Coe Burns's cultic-vocabulary **Workbooks**. The workbooks yield per-worksheet CSV files; the thesis Appendix has a separate KTU findspot table. The native v2 Text-Fabric output adds queryable Burns `entity` nodes to an exact Copenhagen Ugaritic Corpus (CUC) base **without embedding CSV-row JSON at word level**. This v2 path is implemented on PR #69 and remains unreleased until its frozen final head is independently reviewed; no generated Burns corpus is distributed here.

## Source and extraction

Burns, Duncan Coe (2003), *Contents, texts and contexts: a contextualist approach to the Ugaritic texts and their cultic vocabulary*, PhD thesis, University of Sheffield: <https://etheses.whiterose.ac.uk/id/eprint/15038/>.

- `scripts/parse_workbooks_to_csv.py` extracts 45 worksheets to CSV.
- `scripts/parse_appendix_to_csv.py` extracts the separate KTU catalogue to `output/appendix.csv` (requires Poppler `pdftotext`).
- `scripts/sources.py` downloads the two source deposits and checks pinned SHA-256 fingerprints.
- `output/README.md` documents the extraction columns, transcription repair and corrections.
- `CONTEXTUALIST_APPROACH.md` explains Burns's method and interpretation of the labels.

```bash
uv run --no-project scripts/parse_workbooks_to_csv.py
uv run --no-project scripts/parse_appendix_to_csv.py
```

The parsers can download source material if absent. For offline input use `--no-download` or `--input`. Large `Workbooks/`, `Appendix.pdf`, thesis volumes, CSVs, and generated TF outputs are excluded from git. Materialization itself has no source-download fallback.

## Native v2: materialize a queryable CUC extension

```bash
python -m pip install .
ugarit-context-parsing module output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /new/path/burns-native
```

PDF input uses the same normalization and alignment model:

```bash
ugarit-context-parsing module Workbooks \
  --input-format pdf \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /another/new/path/burns-native
```

`module` now chooses the v2 native entity publisher; `entities` remains an alias for experimental callers. Both require an **absent output path**, and reject any output that overlaps the input or CUC directory. Neither deletes, migrates in place, nor overwrites an existing v1 module. To migrate, create a separate v2 directory, verify queries and the local report, and only then switch your consumer's ordered locations. Keep the old directory for rollback; automatic replacement remains intentionally unimplemented.

The exact reviewed CUC dependency is `DT-UCPH/cuc` commit `ad69400f5446e1c8217af01659c7c10ab00c015b`, `tf/0.2.8`. Its required `otype.tf`, `oslots.tf`, tablet/column/line features, and `g_cons.tf` are fingerprinted by size and SHA-256 before a native module is written. CUC is not downloaded or redistributed. A different CUC version or commit is **not** automatically compatible.

The v2 output includes a complete *extended* `otype.tf` and `oslots.tf` warp, preserving the reviewed CUC node IDs and sign slots and appending actual Burns occurrence nodes of `otype=entity`. It does not copy CUC text features. **Load both locations in order** (base, then Burns):

```python
from tf.fabric import Fabric
api = Fabric(
    locations=["/path/to/cuc/tf/0.2.8", "/new/path/burns-native"],
    modules=[""], silent="deep",
).loadAll(silent="deep")
assert api is not None
names = tuple(api.S.search("entity burns_category=divine_name", silent="deep"))
actions = tuple(api.S.search("entity burns_category=cultic_action", silent="deep"))
roots = tuple(api.S.search("entity burns_root=YOUR_ROOT", silent="deep"))
positive = tuple(api.S.search(
    "entity burns_category=personal_name burns_semantic_status=positive_fixed",
    silent="deep",
))
```

An exactly aligned lexical occurrence gets its **own** entity, even when two Burns entries overlap or a label spans multiple CUC words. Scalar node features are `burns_headword`, `burns_root` (if recorded), `burns_category` (the nine source workbook classes), `burns_semantic_status`, `burns_worksheet_role`, and `burns_section`. `burns_headword` faithfully represents the source label; it is **not** a linguistically verified lemma, so no `burns_lemma` is invented. Category-only queries represent source workbook membership and include excluded homographs; combine them with semantic status for positive-only readings. Uncertain, unmatched, and non-textual annotations are retained as counted local audit evidence rather than claimed as exact word matches.

`burns_locus`, `burns_room`, `burns_point`, `burns_depth`, `burns_disputed` are emitted only on the corresponding CUC `tablet` node if **all** applicable Burns observations consistently support that value. Disagreements and missing evidence remain in the local sidecar; no fragment nodes or per-word location duplicates are fabricated. The local `burns-entity-report.json` holds provenance, full source records, entity-to-occurrence mapping, CUC compatibility and alignment/findspot audit. Generated Burns-derived data must stay local.

See [`docs/native-entities.md`](docs/native-entities.md) for a focused invocation/query example. The acceptance gates exercise the actual 45 Workbooks (13,857 rows / 10,419 annotations), reviewed CUC 0.2.8, native Text-Fabric composition and `cfabric-mcp`, plus the separately pinned Appendix. The current audit yields 4,357 exact lexical entity occurrences; 4,993 resolved-line occurrences remain structural-only because exact surface identity is not established. CUC 0.2.8 has no lemma/morphology feature, so the module does not manufacture fuzzy or prefix/suffix matches. The remaining 172 reference-parser failures and 21 parsed-but-missing CUC lines stay explicitly accounted for rather than coerced.

### Explicit v1 compatibility and rollback

The old **six JSON-valued features** are no longer the primary `module` output. Reproduce them only by requesting the explicit compatibility command:

```bash
ugarit-context-parsing module-v1 output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /path/to/legacy-burns-module
```

`module-v1` retains the previous `burns_annotations.tf`, `burns_annotation_ids.tf`, `burns_semantic_statuses.tf`, `burns_worksheet_roles.tf`, `burns_sections.tf`, `burns_headwords.tf` and `burns-module-report.json` schema, including its existing output behavior for compatibility. **Do not load v1 and v2 together:** the two schemas have different meanings and v2 owns the extended warp. To roll back, restore the original base + v1 ordered locations and the retained v1 output. Pending PR #65 hardcodes the old feature inventory and must be reconciled before release.

### Agora status

Agora v1.0.0 and PR `alexsosn/Agora#175` register `cuc-burns` as a CUC-attached `local-module` feature module with an exact parent-base contract. Agora no longer registers or installs the old standalone Burns converter. Users materialize Burns locally and Agora composes it with the reviewed CUC parent.

Fully managed execution — user-local Burns source plus an Agora-managed read-only CUC parent passed to the upstream materializer — remains tracked in open `alexsosn/Agora#135`. Until that orchestration exists, this repository does not advertise a fake one-input materializer, copy CUC into Burns output, or enable a network fallback during materialization.

### Appendix scope

`output/appendix.csv` is a separate 11-column KTU catalogue, not a tenth lexical workbook, and is not silently mixed into the lexical module. The aggregate concordance audit finds 40 reviewed-CUC-mapped tablets with multiple RS numbers; all mapped Appendix findspot conflicts/incompleteness occur inside that set. A cross-source check found no disagreement between Appendix and the 823 tablet-field values the Workbooks policy would publish. No fragment nodes are created because reviewed CUC 0.2.8 supplies no fragment/RS identity mapping.

## License and attribution

### Software license

The repository software is licensed under the **MIT License** (`LICENSE`). It does not relicense Burns's source material, generated Burns-derived data, or CUC.

### Burns source material and generated artifacts

Burns's thesis/Workbooks are © Duncan Coe Burns (2003), available under **CC BY-NC-ND 2.5**. Generated CSV and TF are derived reformatting of those works. The NoDerivatives term is why the generated artifacts are deliberately local and excluded from git. **Do not redistribute** generated CSV/TF artifacts without permission from the copyright holder; obtain the licensed source independently and run the parser locally. The reviewed CUC base retains its own upstream license and is not bundled.
