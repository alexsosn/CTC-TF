# #91 Research: make residual line-drift diagnostics candidate-aware

## Regression

#80 introduced a conservative ±1/±2 line-address audit while production lexical
matching still used one literal headword token tuple. #78 and #79 subsequently
changed production alignment to use the reviewed finite `headword_candidates()`
model, but the line-drift audit kept calling the historical
`_headword_tokens(annotation.headword)`.

The audit is therefore stale for residual `HEADWORD_NOT_FOUND` occurrences
whose production syntax class is non-literal. A neighboring line may contain an
exact `parenthesis_core`, `parenthesis_core_opaque_group`, `slash_left`, or
`slash_right` span while the diagnostic searches an impossible punctuation-
bearing literal string.

This does not alter production anchors, but it makes the reported residual
neighbor-rescue counts incomplete and can misclassify address drift before #81.

## Required semantics

The diagnostic must reuse production candidate generation, not reimplement the
expression grammar.

For each residual `HEADWORD_NOT_FOUND` occurrence and each structurally valid
neighbor offset (-2, -1, +1, +2):

1. obtain the ordered `headword_candidates(annotation.headword)`;
2. exact-match each token tuple with the same `_candidate_spans()` primitive;
3. union distinct word spans across candidate rules;
4. count the neighbor as matched when the union is non-empty;
5. cardinality 1 means one exact neighbor span;
6. cardinality >1 means ambiguous neighbor span;
7. matches on more than one offset remain `multi_neighbor`.

Candidate rule names are not needed in the public aggregate. The output remains
source-safe and diagnostic-only.

## Why span deduplication matters

The diagnostic is about possible textual locations, not candidate-rule
provenance. If two candidate rules ever resolve to the same word span, that is
one neighboring location, not two. Production alignment may preserve rule
provenance separately; line-drift cardinality should count distinct spans.

## Boundary

No reference is automatically shifted. No syntax class is widened. No new TF
feature is emitted. This ticket only makes the diagnostic reflect the matcher
that is already authoritative in production.

The same mismatch should be kept in mind for #81's residual lexical-gap
analysis; #81 must either restrict itself to clean/marker-only expressions or
make its diagnostics candidate-aware explicitly.


## Real-source result

Pinned real Workbooks + reviewed CUC 0.2.8 on GREEN head
`374b44e79e489cb5abd306389da34a5be96fa02d` passed the real-source gate
(run `37041597060`).

Residual lexical denominator after #78/#79:

- `HEADWORD_NOT_FOUND`: **1,841** occurrences.

Candidate-aware neighboring-line outcomes:

- no neighbor exact match: **1,596**;
- unique neighboring exact span: **209**;
- exact matches on multiple neighbor offsets: **36**;
- single-neighbor multi-span ambiguity: **0**.

Compared with the stale literal-only post-#78/#79 report (110 unique / 14
multi-neighbor), production-candidate semantics expose 99 additional unique
rescues and 22 additional multi-neighbor cases.

By syntax class:

- clean: 562 -> 80 unique, 9 multi, 473 none;
- marker-only: 323 -> 30 unique, 5 multi, 288 none;
- parentheses: 911 -> **99 unique, 21 multi, 791 none**;
- slash: 39 -> 0 unique, **1 multi**, 38 none;
- square-bracket exclusive: 6 -> 0 rescues.

Thus the historical 110/14 counts remain correct for the effectively literal
clean/marker-only residual population, but were not complete for the full
post-expression residual set.

Raw matched offsets:

- +1: 120 any matches / 94 unique rescues;
- +2: 56 / 39;
- -1: 71 / 47;
- -2: 45 / 29.

The new evidence strengthens, rather than weakens, the rule against automatic
address shifting: 86.7% of residual misses still have no exact neighboring
candidate hit, and 36 cases match more than one offset. Neighbor evidence remains
diagnostic and source-edition research is required before any mapping rule.

## Conclusion

The regression is confirmed and fixed by reusing the production candidate
generator. No production alignment, reference resolver, or TF publication
semantics changed.
