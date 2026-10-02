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
