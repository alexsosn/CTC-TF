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
- `burns_match_rule_N` (`literal`, `parenthesis_core`, `parenthesis_core_opaque_group`, `slash_left`, or `slash_right`)
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

A Burns headword is a source grouping label, not a certified lemma. `burns_match_rule_N` preserves the exact candidate rule that established the published word span. Failed or
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

Current pinned real-source evidence after the evidenced headword-expression
rules: 7,402 exact lexical occurrences on 5,909 distinct carrier words. The
lane-depth distribution is 4,837 carriers at depth 1, 724 at depth 2, 303 at
depth 3, 30 at depth 4, 2 at depth 5, and 13 at depth 6. The implementation is
dynamic; consumers discover lanes from the feature inventory rather than
assuming a corpus-derived maximum.

The matcher interprets a small reviewed set of non-literal expression classes: a
single balanced non-nested parenthesized group is omitted from the lexical core;
a single token-internal slash supplies exact left/right alternatives; and
bracket/slash markup wholly contained in an already-omitted parenthesized group
may remain opaque. This last rule does not debracket lexical text or assert a
restoration reading. Square brackets that survive into the lexical core and
other complex/mixed punctuation still fail closed.
