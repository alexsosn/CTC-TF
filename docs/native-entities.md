# Native Burns entities: experimental v2 (issue #68)

The primary `module` command now emits **queryable native Text-Fabric entity nodes**, not v1's JSON-valued annotation features. The `entities` command is an alias; the old v1 feature-only format is retained only under the explicit `module-v1` command. This migration is on draft PR #69, not released. Generated Burns-derived artifacts are local-only and cannot be redistributed without permission under the source terms.

```sh
ugarit-context-parsing module output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /new/absent/path/burns-native
```

`--cuc` must point to exact reviewed `DT-UCPH/cuc@ad69400f5446e1c8217af01659c7c10ab00c015b`, `tf/0.2.8`; it must already be on disk. `--input-format pdf` accepts the Workbook PDF tree. Input and output trees must not overlap. Output **must not exist**, even as an empty directory: publication neither overwrites previous output nor silently converts v1 in place.

**Load BOTH locations, in order:** this is an overlay with a *complete extended warp* (`otype.tf`, `oslots.tf`) but it does not copy CUC transliteration/section data or redistribute CUC.

```python
from tf.fabric import Fabric
api = Fabric(
    locations=["/path/to/cuc/tf/0.2.8", "/new/absent/path/burns-native"],
    modules=[""], silent="deep",
).loadAll(silent="deep")
assert api is not None
hits = list(api.S.search("entity burns_category=divine_name", silent="deep"))
roots = list(api.S.search("entity burns_root=YOUR_ROOT", silent="deep"))
positive = list(api.S.search(
    "entity burns_category=personal_name burns_semantic_status=positive_fixed",
    silent="deep",
))
```

Each **entity** is one safely, exactly aligned lexical Burns annotation occurrence, including multiword spans and overlaps. It has scalar `burns_headword`, `burns_category` (nine source workbook categories), `burns_semantic_status`, `burns_worksheet_role`, `burns_section`, and `burns_root` only where Burns supplies it. `burns_headword` is a source label, not a verified linguistic lemma; no `burns_lemma` is invented. Category membership also includes excluded homographs, so filter `burns_semantic_status` when making positive-only queries. Full source rows, source IDs, ambiguous/out-of-CUC alignments and archaeological disagreements are kept in the local `burns-entity-report.json`, not repeated on words or entities.

`burns_locus`, `burns_room`, `burns_point`, `burns_depth` and `burns_disputed` appear on existing CUC `tablet` nodes only when all applicable records supply one consistent value. Missing or contradictory observations stay in the local audit; no fragment nodes or word-level findspots are fabricated. Example: `tablet burns_locus=GP`.

To roll back, keep the previous base + old v1 output. The compatibility invocation is `ugarit-context-parsing module-v1 output --input-format csv --cuc /path/to/cuc/tf/0.2.8 --output /separate/legacy/path`. Do **not** load v1 and v2 simultaneously: they have different node-graph semantics. The v2 CLI refuses to overwrite old modules, protecting foreign data.

The reviewed CUC, synthetic Burns records and `cfabric-mcp` smoke tests have passed. This does **not** establish real Burns workbook completeness, Appendix-to-fragment mappings, full-scale memory/disk performance or a final adversarial review. These remain release blockers in #68; do not merge this draft as a production-ready module.
