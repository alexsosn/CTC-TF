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
