# #97 Research: one-edit Burns↔CUC transcription/orthography residuals

## Starting evidence

#81 identifies 112 clean/marker-only residual occurrences whose cited line has
one unique CUC word at Levenshtein distance 1 after higher-priority neighbor,
exact-boundary and containment evidence is excluded:

- deletion relation: 52;
- substitution: 47;
- insertion: 13.

Edit distance is diagnostic only. It is not an alignment rule.

## Research questions

For exactly that 112-occurrence hierarchy class, aggregate:

- substitution source→CUC code-point pairs;
- inserted CUC code points and start/internal/end positions;
- deleted Burns code points and start/internal/end positions;
- Unicode code-point identity after NFC;
- whether any operation involves a combining mark;
- distinct Burns annotation counts / occurrence multiplicity;
- workbook and worksheet-role concentration.

Use code-point labels such as `U+1E6F>U+0074` rather than lexical strings.

## Operation semantics

The direction is Burns candidate → CUC surface word.

- substitution: same length, one source code point replaced by one CUC code point;
- insertion: CUC has one additional code point;
- deletion: CUC has one fewer code point.

The implementation must derive the unique edit script only after confirming
Levenshtein distance exactly 1.

## Evidence boundary

CI/committed output contains aggregate code-point/position counts only. Never
emit Burns/CUC words, locators, rows, ids, or CUC nodes.

Concrete examples remain local/private.

## Production gate

No generic edit-distance matcher.

Only a recurrent confusion independently demonstrated to be an actual
transliteration/parser convention may become a deterministic normalization
rule, with a dedicated TDD ticket and negative controls.


## Pinned real-source result

Pinned Workbooks + reviewed CUC on the rebased research code reproduce the #81
one-edit denominator exactly:

- one-edit occurrences: **112**;
- distinct Burns annotations: **92**;
- deletion: **52**;
- substitution: **47**;
- insertion: **13**;
- ambiguous distance-1 CUC word candidates excluded from the unique class: **10**;
- combining-mark operations after NFC: **0**.

Repeated-reference inflation is material. Annotation occurrence multiplicity is
82×1, 6×2, 2×3, 1×5 and 1×7. Per-confusion distinct-annotation counts are
therefore authoritative for recurrence, not raw occurrence counts.

### Indel-position ambiguity

A review-derived RED showed that Levenshtein distance 1 does not imply a unique
edit index when repeated characters are present. The final diagnostic enumerates
all valid single-character insertion/deletion indices and reports the position
as `ambiguous` when more than one index yields the same other string.

On the real data:

- deletion positions: 22 ambiguous / 15 end / 14 start / 1 internal;
- insertion positions: 2 ambiguous / 10 internal / 1 end.

This prevents repeated-letter strings from manufacturing positional evidence.

### Recurrent code-point families

The largest raw family is deletion of `U+006D`:

- 22 occurrences;
- only **8 distinct annotations**;
- 20/22 have ambiguous edit position.

Deletion of `U+0079` occurs 8 times across 8 distinct annotations. Other
deletion families have at most five raw occurrences.

Substitution evidence is diffuse. No substitution pair exceeds three raw
occurrences; the repeated three-occurrence families have only two or three
distinct annotations. Insertions are similarly sparse: the largest inserted
code point occurs three times across three annotations.

The aggregate therefore does **not** establish a general Burns↔CUC
transliteration equivalence. In particular, edit distance must not become a
production matcher or normalization table.

The recurrent `U+006D` deletion family is isolated for local/private source
inspection in #103 because its raw recurrence is dominated by only eight
independent Burns annotations and repeated-character ambiguity.

## Production decision

No production alignment change is justified by #97 aggregate evidence.

All 112 cases remain unresolved unless a later ticket establishes a specific
parser, orthographic or morphological relation independently of edit distance.
Concrete examples still require local/private inspection before any narrow rule
can be proposed.
