# #82 Plan: feature-only Burns module migration

## Gate 1 — research-only RED

Before changing the public module writer:

1. add source-safe aggregate collision statistics for exact lexical occurrences;
2. add a synthetic Text-Fabric contract proving an ordinary module may contain
   lane node features + span edge features without `otype`/`oslots`;
3. prove self-edge span membership round-trips/searches correctly, or choose a
   documented non-self encoding before production.

Run the collision audit on pinned Workbooks + reviewed CUC and record the result
in the #82 research file.

## Gate 2 — production RED schema

After the research gate is satisfied, preserve RED tests for a new feature-only
module schema:

- public `module` emits no `otype.tf`, `oslots.tf`, or replacement `otext.tf`;
- base CUC node universe and warp are byte/semantically unchanged after combined
  load;
- one exact single-word occurrence round-trips;
- one multiword occurrence is reconstructable from start word + lane span edge;
- nested/overlapping spans with different starts coexist;
- multiple occurrences sharing one start word occupy deterministic distinct lanes;
- identical-span independent annotations remain distinct;
- lane metadata is scalar and directly TF-searchable;
- failed/ambiguous lexical alignments emit no lexical lane feature on
  line/column/tablet nodes;
- tablet findspots remain limited to existing tablet nodes;
- feature inventory and lane count are deterministic under reversed input order.

## Gate 3 — writer/publication

Implement a dedicated corrected module schema rather than mutating the legacy v1
JSON contract in place.

Writer requirements:

- node + edge features only;
- exact owned-file inventory;
- no foreign TF overwrite;
- deterministic metadata binding to reviewed CUC;
- local lossless report with source/alignment provenance;
- schema/version marker distinct from v1 JSON and entity-v2;
- safe migration to a new output directory or equally strong ownership policy.

## Gate 4 — CLI migration

- `module` -> corrected feature-only schema;
- `module-v1` -> explicit JSON legacy compatibility only if retained;
- retire/remove the extended-warp `entities` product path; do not leave two
  contradictory public models;
- remove entity-v2 implementation/tests/docs once no supported path imports them,
  or quarantine them outside the installed public package only if historical
  preservation is required.

Update README, focused docs, release notes/contracts and help text.

## Gate 5 — real data / consumers

On pinned Workbooks + reviewed CUC:

- exact lexical occurrence accounting is lossless;
- no public lexical feature appears for 4,993 current `HEADWORD_NOT_FOUND` or
  other non-exact cases;
- combined `maxSlot`/`maxNode`/warp are identical to CUC;
- module contains no warp files;
- native TF search works on lane metadata and span edges;
- Context-Fabric/cfabric-mcp consumes the same feature-only module;
- memory/disk cost is reported.

The real-source workflow must track every production/audit file on which these
claims depend.

## Gate 6 — logically independent exact-head review

Review from the consumer/data-model boundary, not from implementation history.
Attack:

- hidden node creation or warp override;
- same-start/identical-span collision loss;
- lane-order nondeterminism;
- phrase metadata accidentally copied as token-level lexical properties;
- structural fallbacks leaking into public features;
- edge endpoints outside CUC word nodes;
- stale v2 entity code/docs/CLI aliases;
- migration/owned-file hazards;
- real-source and downstream CI trigger completeness.

Do not finalize/merge if any of those remain unresolved.
