# Native Burns entity extension (experimental, issue #68)

This is the experimental, **queryable** alternative to the existing `module` command, which still emits six v1 JSON-valued features. Run `entities` explicitly; it never overwrites an existing output directory. The output is local-only Burns-derived material and must not be redistributed without permission under the source terms.

```sh
ugarit-context-parsing entities output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /new/empty-parent/burns-entities
```

`--cuc` must be the exact reviewed Copenhagen Ugaritic Corpus (`DT-UCPH/cuc@ad69400f5446e1c8217af01659c7c10ab00c015b`, `tf/0.2.8`); it must already be present on disk. `--input-format pdf` also accepts the Workbook PDF tree. Neither source, CUC, nor output may overlap, and output must *not exist*, even as an empty directory. Use a distinct new output path on each execution; automated update/replacement is deliberately not yet implemented.

**Load BOTH locations, in order.** This is an overlay with a *complete extended warp* (`otype.tf`, `oslots.tf`) but it deliberately does not copy CUC transliteration/section data or redistribute CUC:

```python
from tf.fabric import Fabric
api = Fabric(locations=["/path/to/cuc/tf/0.2.8", "/new/empty-parent/burns-entities"], modules=[""], silent="deep").loadAll(silent="deep")
assert api is not None
hits = list(api.S.search("entity burns_category=divine_name", silent="deep"))
root_hits = list(api.S.search("entity burns_root=YOUR_ROOT", silent="deep"))
```

An **entity** is one safely, exactly aligned Burns annotation occurrence. It has a scalar `burns_headword`, `burns_category` (one of nine source workbook categories), `burns_semantic_status`, `burns_worksheet_role`, `burns_section`, and `burns_root` only where supplied by Burns. Its `oslots` contains the sign slots of all words in a multiword occurrence. Overlapping occurrences receive separate entity nodes, not arrays/JSON on one word. `burns_headword` is Burns's source label; no `burns_lemma` is emitted because the source contains inflected forms, names, editorial marks and phrases. Source rows, IDs, excluded/ambiguous and out-of-CUC alignments, and archaeological disagreements are preserved in the **local** `burns-entity-report.json`, not repeated on every entity or word.

`burns_locus`, `burns_room`, `burns_point`, `burns_depth`, and `burns_disputed` appear on existing `tablet` nodes only when all applicable rows supply exactly one non-conflicting value. Empty/missing/conflicting observations remain missing in TF and are explicitly inventoried in the local sidecar; no fragment nodes or speculative per-word findspots are fabricated. A tablet query looks like `tablet burns_locus=GP`.

The experimental implementation and tests preserve existing CUC node IDs and append entity node IDs above the reviewed CUC maximum, validated on the exact CUC base with synthetic Burns rows, native Text-Fabric searches and cfabric-mcp. That does **not** establish complete real Burns-source coverage, exact folder spelling, Appendix/fragment concordance, or corpus-scale disk/memory performance. Those gates and a logically independent final adversarial review remain required before #68 is considered fixed or the default v1 `module` command is replaced.
