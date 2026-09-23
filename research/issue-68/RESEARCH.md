# #68 Research: native, queryable Burns annotations

## Confirmed defect

`module.py` on `master@4994a45c53a73c09a4939731bc56af585b3ba30a` writes six string-valued TF features. Every value is a JSON array, even for projections; the canonical feature repeats raw rows, excavation data, identities and alignment diagnostics on each word participating in a span. The v1 tests verify JSON fidelity but never assert successful native TF lexical/category queries. This is a user-facing data-model defect, not a cosmetic format choice.

## Source domain (checked against Burns 2003, volume 1, chapter 5, p. 187)

The nine workbooks have an explicit source-defined classification:

| Workbook | Classification | Proposed stable slug |
|---|---|---|
| I | Divine Names | `divine_name` |
| II | Personal Names | `personal_name` |
| III | Geographical Names | `geographical_name` |
| IV | Cultic Jargon | `cultic_jargon` |
| V | Cultic Commodities | `cultic_commodity` |
| VI | Cultic Locations | `cultic_location` |
| VII | Cultic Times and Events | `cultic_time_event` |
| VIII | Cultic Personnel | `cultic_personnel` |
| IX | Cultic Actions | `cultic_action` |

Source: https://etheses.whiterose.ac.uk/id/eprint/15038/1/269335_vol1.pdf, chapter 5, section 3(a)(1), indexed as https://etheses.whiterose.ac.uk/id/eprint/15038/1/269335_vol1.pdf ; `CONTEXTUALIST_APPROACH.md` independently lists the same nine categories. The category is derived from an audited ordinal, NOT a guessed basename split. Workbook label/path must not be silently treated as category authority when its ordinal disagrees with a verified label; real directory spellings require local-source audit before enforcing spelling.

Worksheet roles 1–5 (`prime_gp`, `prime_ph`, `derived_common`, `derived_gp_only`, `derived_ph_only`) are *not* those entity classes. The section-dependent semantic statuses (`positive_fixed`, `probable_cultic`, `no_secure_cultic`, `homograph_excluded`, `unsupported`) are a separate interpretation axis, not additional workbooks or the status of archaeological findspots.

`headword` is a source transcription/group label, not a certified linguistic lemma (multiword values, editorial markers and inflected forms exist). `root` is populated principally in workbook IX; do not fabricate roots or lemmas for missing values. Section β homographs may be explicitly excluded rather than treated as positive assertions: document query semantics by status.

## Text-Fabric architecture limit

The reviewed CUC (`DT-UCPH/cuc@ad69400...`, `tf/0.2.8`) owns `otype` and `oslots`: sign slots followed by word/line/column/tablet nodes, no `entity` or `fragment` nodes. Text-Fabric documentation states modules contain weft features around the same base warp: https://annotation.github.io/text-fabric/tf/about/datamodel.html . A feature-only overlay can express native scalar predicates on existing nodes but *cannot* create a distinct TF entity node per Burns occurrence; changing `otype`/`oslots` would be a new derived CUC-compatible corpus, requiring remapping and consumer review. Do not label the initial overlay 'native entities'.

Collision cases already present in `tests/test_burns_tf_module.py`: source `bʿl` and `bʿl*` both align to word 8; `bʿl mlk`, `mlk x` and `mlk` all overlap at word 11. Copying the phrase label to every word would make individual-word queries falsely report a phrase headword as a lexical lemma. A scalar single-value field cannot store both independent occurrences. Native category flags are naturally many-to-many by separate features; a per-word headword/root feature must have an explicit collision policy and sidecar coverage counters, rather than silent last-write-wins or JSON/semicolon lists.

Alignment already distinguishes word spans, line-only matches (ambiguous or headword not found), tablet-only matches, and unselected cases. Only exact lexical word spans warrant token-level category membership; ambiguous candidates must not become word-level hits.

Findspots (`locus`, `room`, `point`, `depth`, `disputed`) are source-row observations, sometimes repeated or potentially contradictory for one tablet. For a consistent KTU-to-CUC tablet, attach one value to that tablet; for conflicts do not choose arbitrarily or concatenate. No CUC fragment node currently exists, so fragment-scoped properties remain in sidecar until a verifiable fragment mapping exists. The Appendix is not part of the Workbooks materializer and must be reviewed separately before being treated as a source of truth.

## Real-source acceptance evidence

The ephemeral CI acceptance gate now downloads the pinned public Burns Workbooks, parses them runner-locally, composes the result with reviewed CUC 0.2.8, and discards all source/derived files after the job. Exact run 35852364383 on head `22d9705337373221930bd85eed5a805740aabf38` passed without uploading or logging source rows, lexical labels or locators.

Aggregate-only inventory from that run:

- 45 Workbook PDFs → 13,857 source records → 10,419 normalized annotations.
- Alignment dispositions: 5,007 aligned, 40 ambiguous, 748 non-textual, 4,343 out of reviewed CUC, 80 partial, 201 unresolved references.
- Native lexical coverage: 4,316 exact lexical word-span occurrences; 4,964 aligned occurrences remain exact-structural line anchors because the source headword was not found; 16 aligned tablet-only occurrences.
- Unresolved reference split: 180 parser failures plus 21 parsed targets whose line is absent from reviewed CUC.
- Parser-failure reasons are now classified without emitting source strings: `invalid_ktu=85`, `uncertain_marker=49`, `malformed_structure=27`, `duplicate_target=10`, `unsupported_wording=8`, `unsupported_punctuation=1`.
- Reference statuses across all annotations: `parsed=9491`, `non_textual=748`, `invalid_ktu=85`, `malformed=37`, `unsupported=58`.
- Native output was 23,903,769 bytes; peak Linux RSS was 452,332 KiB.
- Tablet findspot audit still reports 59 conflicts, 28 incomplete mapped tablets and 5,430 unmapped source records; these remain sidecar/audit information rather than guessed TF values.

This evidence validates parser/accounting, reviewed-CUC composition, native publication and aggregate coverage on the actual Workbooks. It does **not** establish semantic completeness. In particular, the 4,964 `headword_not_found` occurrences require evidence-based lexical matching analysis, and the 180 reference parser failures must not be turned into exact anchors merely to improve coverage. The Appendix and any fragment-level concordance remain unaudited.

## Decision gate

Do not release v1 as a user-queryable lexical module. Develop a v2 design that prioritizes 9 category predicates and safe lexical/root queries, keeps full source/alignment in the local report, scopes consistent excavation metadata to tablets, and explicitly exposes any overlay limitation on overlapping span identity. Before calling #68 fixed, independently verify a genuine entity/span architecture or get explicit approval for a bounded overlay contract, run native `Fabric` searches, audit local source collisions and review cfabric-mcp/Agora consumers. Retain existing publication safety and source non-redistribution.
