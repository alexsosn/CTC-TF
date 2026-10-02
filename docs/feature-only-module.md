# Burns feature-only CUC module

The primary `ugarit-context-parsing module` command writes a Text-Fabric module
around the exact reviewed CUC warp. The output contains ordinary node/edge
features only: it does **not** contain `otype.tf`, `oslots.tf`, replacement
`otext.tf`, or any Burns-created nodes.

```sh
ugarit-context-parsing module output \
  --input-format csv \
  --cuc /path/to/cuc/tf/0.2.8 \
  --output /new/absent/path/burns-module
```

`--input-format pdf` accepts the Workbook PDF tree. `--cuc` must point to
reviewed `DT-UCPH/cuc@ad69400f5446e1c8217af01659c7c10ab00c015b`,
`tf/0.2.8`. Output must be absent and must not overlap source or CUC.

Load the base first and the Burns module second:

```python
from tf.fabric import Fabric

api = Fabric(
    locations=["/path/to/cuc/tf/0.2.8", "/new/absent/path/burns-module"],
    modules=[""],
    silent="deep",
).loadAll(silent="deep")
assert api is not None
```

## Occurrence lanes

An exactly aligned Burns lexical occurrence is carried by the first existing CUC
word in its span. Metadata is scalar and lane-numbered:

- `burns_occurrence_id_N`
- `burns_annotation_id_N`
- `burns_headword_N`
- `burns_root_N` where Burns supplies one
- `burns_category_N`
- `burns_semantic_status_N`
- `burns_worksheet_role_N`
- `burns_section_N`
- `burns_span_length_N`

For a multiword occurrence, `burns_span_N` is an edge from the carrier to the
remaining existing CUC word nodes. The carrier is the implicit first member. A
single-word occurrence has span length 1 and no outgoing edge.

If two independent Burns occurrences start at the same word they occupy separate
lanes, assigned deterministically from stable occurrence identity. Lane count is
data-derived; consumers should discover available lane features instead of
hard-coding a maximum.

Examples:

```python
# exact occurrences in lane 1
names = tuple(api.S.search(
    "word burns_category_1=divine_name",
    silent="deep",
))

# query multiword members for lane-1 divine-name occurrences
members = tuple(api.S.search(
    """s:word burns_category_1=divine_name
m:word
s -burns_span_1> m""",
    silent="deep",
))
```

A Burns headword is a source grouping label, not a certified lemma. Failed or
ambiguous lexical narrowing is kept in the local report and does not emit
lexical features on CUC line/column/tablet nodes.

## Tablet findspots

`burns_locus`, `burns_room`, `burns_point`, `burns_depth`, and
`burns_disputed` are emitted only on an existing CUC tablet when all applicable
Workbook observations agree. Conflict/incomplete evidence stays in the local
report. No fragment nodes are synthesized.

## Local report and migration

`burns-feature-module-report.json` contains source/alignment provenance,
occurrence-to-lane/span mapping, exact CUC compatibility, and findspot audit
information. It is local Burns-derived data and is not distributed by this
repository.

The earlier extended-warp `entity` experiment is retired: there is no
`entities` CLI alias and no Burns-owned warp. The prior JSON feature module is
available only through explicit `module-v1` compatibility invocation.

Current pinned real-source evidence after the bounded #78 headword-expression
rules: 7,308 exact lexical occurrences on 5,924 distinct carrier words, with a
current maximum lane depth of 6. The implementation remains dynamic because
later restoration/morphology work may increase multiplicity.

The supported expression rules remain deliberately narrow: one balanced,
non-nested parenthesized group is omitted before exact matching, and exactly one
inline slash in one token generates two alternative exact candidates. Distinct
matching spans remain explicit ambiguity. Square brackets, nested/multiple
parentheses, parenthesis+slash combinations, standalone/multiple slashes and
morphological guesses remain fail-closed.
