# #98 Research: multi-token partial/zero-overlap Burns residuals

## Starting boundary

#81 separates the clean/marker-only residual population after expression syntax,
candidate-aware neighbor evidence, and exact token-boundary diagnostics.

The largest unresolved families are:

- partial exact-token overlap: **313** occurrences;
- zero exact-token overlap: **200**;
- all tokens present but reordered: **8**;
- all tokens present in order but non-contiguous: **2**.

Partial overlap is especially concentrated in Workbook I (189 occurrences).

This ticket focuses on **multi-token** Burns candidates. Single-token containment
and one-edit families belong to #96/#97.

## Research questions

For every multi-token clean/marker-only `HEADWORD_NOT_FOUND` occurrence that has
no candidate-aware neighbor evidence and no exact full-expression
split/merge window, record source-safe structural signatures:

1. Burns token count and cited CUC line word count;
2. exact-token presence mask by Burns token position, e.g. `101` means only
   tokens 1 and 3 occur exactly somewhere on the cited line;
3. exact-hit count and unmatched-token count;
4. whether all exact hits can be realized in Burns order on the CUC line;
5. for each unmatched Burns token, whether the cited line has:
   - exactly one containing CUC word;
   - exactly one distance-1 CUC word after containment precedence;
   - multiple such candidates;
   - no local containment/edit-1 evidence;
6. occurrence-level count of cases with exactly one unmatched token and a unique
   containment/edit-1 candidate;
7. workbook and worksheet-role concentration;
8. distinct Burns annotation counts / occurrence multiplicity for recurrent
   signatures.

These diagnostics do not pair tokens to CUC words as a new alignment algorithm.
They only characterize why a multi-token expression fails exact matching.

## Source/privacy boundary

Committed/CI output may contain only generic masks, token counts, distance/
candidate cardinality buckets, workbook numbers, generic worksheet roles and
integer counts.

Never emit Burns tokens, CUC words, KTU locators, source rows/pages,
annotation/occurrence ids, or node ids. Concrete cases remain local/private.

## Interpretation boundary

A `101` signature does not mean token 2 is a morphological variant. A unique
containment or edit-1 candidate for one missing token is still only a diagnostic
hypothesis.

Possible explanations to inspect locally include:

- one inflected/cliticized token inside an otherwise literal phrase;
- grouping labels with epithets/modifiers not present at the cited occurrence;
- local token split/merge;
- transcription/editorial differences;
- parser cell reconstruction;
- reference/edition disagreement beyond ±1/±2;
- genuine textual disagreement.

## Production gate

No broad partial-overlap matcher and no “match the tokens that happen to fit”.

Any production rule must be split into its own ticket and justified
independently of partial-overlap frequency, with exact ambiguity behavior and
negative controls.
