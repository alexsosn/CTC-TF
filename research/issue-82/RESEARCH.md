# #82 Research: restore Burns as a feature-only CUC Text-Fabric module

## Architectural correction

Burns is an annotation module around the reviewed CUC warp. CUC owns every node
and the warp features `otype` / `oslots`. The public Burns module must therefore
contain only ordinary node/edge features over existing CUC nodes.

This restores the contract established in #21 and reverses the extended-warp
experiment introduced by #68/#69.

Text-Fabric's own data model is explicit:

- `otype` and `oslots` define the warp;
- all other node and edge features are wefts;
- datasets containing wefts but no warp are modules, and those modules are
  constructed around an existing dataset's warp;
- ordinary directed edge features can connect existing nodes and are directly
  usable as search relations.

References:
- https://annotation.github.io/text-fabric/tf/about/datamodel.html
- https://annotation.github.io/text-fabric/tf/core/fabric.html
- https://annotation.github.io/text-fabric/tf/about/searchusage.html

The current public `module` route violates this contract by appending
`otype=entity` nodes and publishing replacement `otype.tf`/`oslots.tf`.

## Representation requirements

The corrected representation must preserve all **exact lexical occurrences**
without inventing nodes and without JSON/delimited multi-values in ordinary TF
features.

Required cases:

1. single-word occurrence;
2. multi-word occurrence;
3. nested/overlapping occurrences with different starts;
4. multiple independent occurrences sharing the same start word;
5. multiple annotations with the exact same span;
6. scalar queryability of occurrence metadata (category, status, headword, root,
   worksheet role, section);
7. exact span reconstruction using only TF features;
8. no lexical feature emitted for `HEADWORD_NOT_FOUND`, ambiguous-line,
   ambiguous-span, out-of-CUC, non-textual or unresolved occurrences;
9. consistent archaeological metadata may remain on existing CUC tablet nodes.

## Why one scalar feature per word is insufficient

A TF node feature is single-valued. Existing Burns data contains overlapping
annotations and words participating in multiple Burns annotations. Copying a
phrase-level headword to every member word also falsely suggests that the phrase
label is a lexical property of each token.

Adding new annotation/entity nodes solved multiplicity at the cost of violating
the module contract. A feature-only schema needs an explicit multiplicity
strategy on existing nodes.

## Candidate: start-word lanes

Represent each exact lexical occurrence on the **first CUC word of its span**.

For lane N, the start word receives scalar features such as:

- `burns_occurrence_id_N`
- `burns_annotation_id_N`
- `burns_headword_N`
- `burns_root_N` when supplied
- `burns_category_N`
- `burns_semantic_status_N`
- `burns_worksheet_role_N`
- `burns_section_N`
- `burns_span_length_N`

and an ordinary valueless edge feature:

- `burns_span_N`: start word -> all CUC word nodes in that occurrence span,
  including the start word itself if Text-Fabric round-trip/search proves
  self-edges are safe.

Lanes are assigned deterministically **per start word** by sorting occurrences by
stable identity. Different start words reuse lane numbers. A second lane is
needed only when two exact Burns occurrences share the same first CUC word.

Advantages:

- no new nodes or warp;
- phrase metadata lives on one explicit carrier instead of being copied as if it
  were token-level morphology;
- a span is recoverable from a normal TF edge feature;
- overlapping spans with different starts coexist naturally;
- same-start collisions remain lossless through lanes;
- all values remain ordinary scalar TF values.

Trade-off:

- precise combined metadata queries must target lane-specific features. If the
  real maximum lane depth is small, this is tractable and honest. If it is large,
  the design should be reconsidered before implementation.

## Alternatives rejected or insufficient

### Copy metadata to every member word

Fails semantic scope and still needs a multiplicity encoding when annotations
overlap on the same word.

### JSON / delimiter lists

Technically feature-only but repeats the v1 usability defect and prevents native
scalar search semantics.

### One generic valued span edge

An edge feature has one value for one source/target pair. Multiple Burns
occurrences with the same start/span would collide.

### One feature per occurrence

Lossless but creates thousands of dynamically named features and is unusable as
a stable module schema.

### Reusing line/tablet nodes as overflow carriers

Semantically false and directly violates the requirement that structural
fallbacks remain audit-only.

## Research gate: real collision inventory

Before freezing the lane schema, measure the 4,357 currently exact lexical
occurrences on pinned Workbooks + reviewed CUC:

- exact occurrence count;
- number of distinct start words;
- histogram of occurrences per start word;
- maximum lane depth;
- span-length histogram;
- histogram/max multiplicity of identical start+span collisions;
- starts containing multiple distinct spans;
- starts containing multiple Burns categories/statuses.

This is aggregate-only CI evidence; no source lexical strings or locators may be
logged.

The collision inventory must be recomputed after #78/#79 lexical widening before
a future release freeze. #82 may establish the schema against current exact
evidence, but must not hard-code a maximum that later lexical fixes can exceed.

## Schema stability strategy

Do not hard-code a corpus-derived maximum lane into parser logic. Build as many
lane feature families as the supplied exact alignments require, deterministically.
The module report records `max_lane` and feature inventory. Consumers discover
available lane features from the TF inventory.

If downstream tools need an ergonomic “any lane” query, provide a helper/query
builder later; do not collapse lane identity into lossy aggregate scalar flags.

## Publication boundary

The public module must satisfy:

- no `otype.tf`;
- no `oslots.tf`;
- no `otext.tf` replacement;
- every feature node id belongs to reviewed CUC;
- every span edge source/target belongs to reviewed CUC word nodes;
- combined CUC + Burns has identical `maxSlot`, `maxNode`, node types and
  `oslots` to base CUC;
- structural fallback alignments appear only in the local report/accounting;
- tablet findspots, where policy permits, are node features only on existing CUC
  tablet nodes.

## Migration

Treat the corrected feature-only product as a new module schema, not as v1 JSON
and not as the #69 entity-node v2 artifact.

The public `module` command must select the corrected schema. The extended-warp
`entities` route must not remain a competing advertised product. Existing local
entity-v2 artifacts are not silently upgraded in place.

The old JSON `module-v1` compatibility path can remain temporarily if needed for
rollback, but it must stay explicitly legacy and must not be confused with the
new public module.

## Open evidence before implementation

1. Real start-word collision/lane inventory.
2. Synthetic Text-Fabric proof that an edge-only module with self-edge span
   membership saves, reloads with the base warp unchanged, and is queryable via
   TF Search.
3. Context-Fabric/cfabric-mcp composition proof for the proposed lane features.
