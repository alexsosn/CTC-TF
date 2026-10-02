# CTC-TF / ugarit-context-parsing

Local extraction and Text-Fabric materialization of Duncan Coe Burns's cultic-vocabulary **Workbooks**. The workbooks yield per-worksheet CSV files; the thesis Appendix has a separate KTU findspot table. The primary Text-Fabric product is a **feature-only module over the existing Copenhagen Ugaritic Corpus (CUC) warp**: Burns adds queryable node/edge features on existing CUC words/tablets, never new nodes and never replacement `otype.tf`/`oslots.tf`. No generated Burns corpus is distributed here.

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

## Feature-only module over reviewed CUC

```bash
python -m pip install .
ugarit-context-parsing module output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /new/path/burns-module
```

PDF input uses the same normalization/alignment path:

```bash
ugarit-context-parsing module Workbooks \
  --input-format pdf \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /another/new/path/burns-module
```

The exact reviewed dependency is `DT-UCPH/cuc@ad69400f5446e1c8217af01659c7c10ab00c015b`, `tf/0.2.8`. Required CUC files are fingerprinted before materialization. CUC is not copied, downloaded, or redistributed by the module command.

The generated directory is a real Text-Fabric **module/weft**. It contains Burns node/edge features and a local report, but **no `otype.tf`, `oslots.tf`, or replacement `otext.tf`**. Loading the module therefore leaves the CUC slot/node universe and warp unchanged:

```python
from tf.fabric import Fabric

api = Fabric(
    locations=["/path/to/cuc/tf/0.2.8", "/new/path/burns-module"],
    modules=[""],
    silent="deep",
).loadAll(silent="deep")
assert api is not None
```

### Exact lexical occurrences: deterministic lanes

Burns occurrences that have an exact lexical CUC word span are stored on the **first existing CUC word** of that span. Multiple independent Burns occurrences starting at the same word use deterministic lane-numbered feature families:

- `burns_occurrence_id_N`
- `burns_annotation_id_N`
- `burns_headword_N`
- `burns_root_N` when supplied
- `burns_category_N`
- `burns_semantic_status_N`
- `burns_worksheet_role_N`
- `burns_section_N`
- `burns_span_length_N`
- edge `burns_span_N` from the carrier to subsequent CUC words in a multiword span.

The carrier itself is the implicit first span member. A one-word occurrence has `burns_span_length_N=1` and no outgoing span edge. This avoids both invented annotation nodes and the false claim that a multiword phrase label is a lexical property of every member token.

Example queries:

```python
# One specific lane.
divine = tuple(api.S.search(
    "word burns_category_1=divine_name",
    silent="deep",
))

# Multiword members for lane-1 divine-name occurrences.
spans = tuple(api.S.search(
    """s:word burns_category_1=divine_name
m:word
s -burns_span_1> m""",
    silent="deep",
))
```

Lane count is derived from the supplied exact alignments rather than hard-coded. On the current pinned real-source audit, 7,253 exact lexical occurrences occupy 5,880 start words. Lane-depth distribution is 4,913 starts at depth 1, 633 at depth 2, 290 at depth 3, 29 at depth 4, 2 at depth 5, and 13 at depth 6. Consumers must inspect the feature inventory/report rather than hard-code a maximum.

`burns_headword_N` is the source headword label, **not** a verified lemma. The matcher now interprets two narrowly evidenced headword-expression classes: one balanced non-nested parenthesized group contributes the exact **core with that group omitted**, and one token-internal slash contributes exact left/right alternatives. This raises the pinned real-source exact count from 4,357 to 7,253. Another 1,991 resolved-line occurrences still have no exact lexical span, and 275 have multiple exact candidate spans; those remain in the local alignment report and are **not** emitted as lexical features on line/tablet nodes. Square-bracket restoration semantics and more complex/mixed expressions remain separate research rather than being hidden behind fuzzy matching.

### Tablet-scoped excavation observations

`burns_locus`, `burns_room`, `burns_point`, `burns_depth`, and `burns_disputed` may appear on an existing CUC `tablet` node only when all applicable Workbook observations consistently support that value. Conflicts/incomplete evidence remain in the local report. No fragment, line, word, or annotation node is invented for findspot data.

The local `burns-feature-module-report.json` stores source/alignment provenance, lane/span identities, CUC compatibility, and findspot audit information. Generated Burns-derived data remain user-local under the source terms.

The `module` command requires an **absent output path** and rejects output overlapping the source or CUC directory. It stages the complete feature module and publishes with an exclusive no-replace operation. The experimental extended-warp `entities` CLI from the earlier #68/#69 design has been retired.

### Explicit v1 compatibility and rollback

The old **six JSON-valued features** are no longer the primary `module` output. Reproduce them only by requesting the explicit compatibility command:

```bash
ugarit-context-parsing module-v1 output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /path/to/legacy-burns-module
```

`module-v1` retains the previous `burns_annotations.tf`, `burns_annotation_ids.tf`, `burns_semantic_statuses.tf`, `burns_worksheet_roles.tf`, `burns_sections.tf`, `burns_headwords.tf` and `burns-module-report.json` schema, including its existing output behavior for compatibility. Treat v1 and the corrected lane schema as separate module versions; materialize them into separate directories and load only the one your consumer expects. To roll back, restore the original base + retained v1 output.

The older standalone converter remains available under `convert` for compatibility. It creates a **different corpus**, with row slots and `worksheet`/`section`/`entry` nodes rather than CUC word/sign structure, and emits `conversion-report.json`; it is deprecated and not a native CUC module.

### Agora status

`agora.materializer.json` currently declares **legacy single-input** CSV and PDF materializers invoking the standalone `convert` command. This is not a native v2 installation, even when Agora's legacy manifest validation passes. The public `module` CLI is the local queryable path; Context-Fabric/cfabric-mcp can load the verified CUC and native Burns directories as ordered locations. The two-input parent-resource requirement in `alexsosn/Agora#135` is **open and explicitly deferred to the first release after Agora 1.0**; Burns migration tracker #29 therefore remains a separate future integration task. We do not advertise a fake one-input materializer, copy CUC into Burns, or enable a network fallback. The manifest is intentionally unchanged pending that work.

### Appendix scope

`output/appendix.csv` is a separate 11-column KTU catalogue, not a tenth lexical workbook, and is not silently mixed into the lexical module. The aggregate concordance audit finds 40 reviewed-CUC-mapped tablets with multiple RS numbers; all mapped Appendix findspot conflicts/incompleteness occur inside that set. A cross-source check found no disagreement between Appendix and the 823 tablet-field values the Workbooks policy would publish. No fragment nodes are created because reviewed CUC 0.2.8 supplies no fragment/RS identity mapping.

## License and attribution

### Software license

The repository software is licensed under the **MIT License** (`LICENSE`). It does not relicense Burns's source material, generated Burns-derived data, or CUC.

### Burns source material and generated artifacts

Burns's thesis/Workbooks are © Duncan Coe Burns (2003), available under **CC BY-NC-ND 2.5**. Generated CSV and TF are derived reformatting of those works. The NoDerivatives term is why the generated artifacts are deliberately local and excluded from git. **Do not redistribute** generated CSV/TF artifacts without permission from the copyright holder; obtain the licensed source independently and run the parser locally. The reviewed CUC base retains its own upstream license and is not bundled.
