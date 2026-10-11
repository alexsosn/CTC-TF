# #80 Research: Burns↔CUC line-address drift audit

## Question

A `HEADWORD_NOT_FOUND` occurrence proves that Burns resolved to an existing CUC line key but the current exact lexical matcher found no span on that line. It does **not** prove that Burns and CUC line numbering/segmentation correspond at that locus.

This ticket tests the narrower hypothesis that some apparent lexical failures are valid-but-shifted structural references (for example Burns line N corresponding textually to CUC line N+1).

## Scope

Audit only. Do not change production reference resolution or silently shift any Burns address.

The unit of analysis is a `HEADWORD_NOT_FOUND` occurrence with an exact `context_line_node`.

For each such occurrence:

1. recover the authoritative CUC `(tablet,column,line)` identity of `context_line_node` from the reviewed index;
2. keep the current headword normalization/matching semantics unchanged;
3. test exact contiguous headword matches on existing neighbor lines at offsets `-2,-1,+1,+2`;
4. never cross a tablet or column boundary;
5. record only aggregate/source-safe counts.

## Why this is independent of #77/#78

#77 established that punctuation-bearing Burns headwords systematically defeat the literal matcher. That does not answer whether some clean or marker-only misses also land on a neighboring CUC line.

This audit uses the current exact matcher deliberately. Expression expansion from #78 must be measured separately later so address drift is not conflated with a changed lexical model.

## Safe outcome model

For each `HEADWORD_NOT_FOUND` occurrence classify:

- `no_neighbor_match`: no exact span in any available neighbor;
- `unique_neighbor`: exactly one neighboring offset has exactly one exact span;
- `multi_neighbor`: exact matches occur at more than one neighboring offset;
- `ambiguous_neighbor_span`: only one neighboring offset matches, but it contains more than one exact span.

Aggregate:

- total audited misses;
- available-neighbor counts by offset;
- matched-neighbor offsets by `-2,-1,+1,+2`;
- outcome counts;
- unique-rescue offset counts;
- syntax class of rescued vs non-rescued occurrences using the #77 source-safe classifier;
- consecutive same-offset run lengths within one CUC tablet+column, reported only as a histogram.

A run is diagnostic evidence only. It must not become an automatic offset rule.

## Structural identity

Do not trust the authored target's optional column alone. Build a reverse map from `index.line_nodes[(tablet,column,line)] -> line_node` and require each analyzed `context_line_node` to resolve to exactly one structural identity. This handles bare-line references that were uniquely resolved by the production aligner.

If the index is internally inconsistent or a context line cannot be reversed exactly, fail the audit rather than guessing.

## Interpretation gate

A nearby lexical rescue can be accidental, especially for short/common headwords. Therefore:

- a unique neighbor match is not automatically a numbering correction;
- multiple neighbor matches are explicit ambiguity;
- same-offset runs are stronger evidence than isolated rescues but still require source/editorial confirmation;
- no production shift is allowed in #80 unless an independently sourced numbering convention is established.

## Privacy

CI/default output is aggregate only. Do not emit Burns headwords, KTU/reference strings, tablet labels, column labels, line numbers tied to a source record, annotation/occurrence IDs, or CUC line text.

## Follow-up

If a strong systematic offset pattern appears, create a dedicated implementation/research child issue for that source-supported mapping. If rescues are sparse/isolated, close #80 as evidence against line drift being a major cause and pass the residual population to #81.


## Real-source result (PR #84)

Pinned real Workbooks + reviewed CUC 0.2.8 passed on GREEN head `7ef4bd025c38119955cb54c7fc4d3222ed771a73` (Tests `37001859780`; real-source workflow `37001859845`).

All 4,993 current `HEADWORD_NOT_FOUND` occurrences were audited with the unchanged exact-contiguous matcher against existing neighboring lines inside the same CUC tablet+column.

### Aggregate outcomes

- no neighbor exact match: **4,869**
- exactly one neighboring offset with one exact span: **110**
- exact matches at multiple neighboring offsets: **14**
- one neighboring offset with multiple exact spans: **0**

Thus a unique neighboring exact hit exists for only **2.20%** of all current misses; any neighboring exact hit exists for **2.48%**. Line-address drift is therefore not a dominant explanation for the full 4,993-case gap.

Available neighboring lines and raw matching offsets:

| offset | neighbor exists | any exact match | unique rescue |
|---:|---:|---:|---:|
| -2 | 4,581 | 27 | 20 |
| -1 | 4,797 | 37 | 28 |
| +1 | 4,871 | 55 | 42 |
| +2 | 4,740 | 27 | 20 |

The +1 direction is somewhat larger, but isolated lexical hits are not sufficient evidence for remapping.

### Interaction with #77 syntax classes

All neighboring exact rescues come from the residual classes whose punctuation can already be normalized by the current matcher:

- clean failures: 562 total → 80 unique neighbor, 9 multi-neighbor, 473 none;
- marker-only failures: 323 total → 30 unique neighbor, 5 multi-neighbor, 288 none;
- parentheses failures: 4,039 → **0** neighbor rescues;
- slash-only failures: 63 → **0**;
- square-bracket-only failures: 6 → **0**.

So the `() [] /` problem remains an expression-semantics problem, not a line-number problem. Among the 885 clean/marker-only misses, however, 124 (14.0%) have at least one neighboring exact hit. That residual deserves local structural investigation rather than morphology-first assumptions.

### Same-offset runs

Most unique rescues are isolated, but the audit found several consecutive same-offset runs inside one tablet+column:

- `-1`: 18 singleton runs and one run of **7**;
- `+1`: 21 singleton runs, three runs of **3**, one run of **4**, one run of **6**;
- `+2`: 17 singleton runs and one run of **2**;
- `-2`: 19 singleton runs.

The long `-1/+1` runs are stronger than isolated lexical coincidences but still do not establish a mapping rule. Follow-up #85 was opened to inspect those actual loci privately against Burns and CUC/KTU segmentation and determine whether a source-supported structural offset exists.

## Decision

#80 does not justify any automatic neighboring-line fallback. The audit shows:

1. line drift cannot explain the mass lexical gap;
2. a non-trivial minority of clean/marker-only residual misses has neighboring exact evidence;
3. local consecutive ±1 runs warrant dedicated source-edition research (#85);
4. production reference resolution remains unchanged until that research establishes a structural rule independent of the searched headword.

The remaining non-neighbor residuals continue to #78/#79/#81 as appropriate.
