# #95 Research: exact Burns↔CUC token-boundary cases

## Starting evidence

#81 finds 19 clean/marker-only residual occurrences where the normalized Burns
candidate and one contiguous CUC word window have exactly the same concatenated
consonants but different token boundaries.

This is stronger evidence than substring/edit-distance similarity but does not,
by itself, authorize general whitespace-insensitive alignment.

## Questions

For all 19 real occurrences, measure without exposing source strings:

- Burns candidate token count;
- CUC candidate-window word count;
- Burns and CUC token-length signatures;
- direction: `merge`, `split`, or `resegment`;
- candidate-window cardinality on the cited line;
- workbook number and worksheet role;
- whether the occurrence also has ±1/±2 neighbor evidence.

## Evidence boundary

Committed/CI output is aggregate-only. It may expose integer token lengths and
counts but never Burns/CUC lexical strings, source rows/pages, locators,
annotation/occurrence ids, or CUC node ids. Concrete lexical examples stay
local/private.

## Production decision

A production rule requires:
1. genuine segmentation rather than parser corruption or distinct grouping;
2. exact consonantal sequence identity;
3. one unique contiguous CUC window;
4. explicit ambiguity for repeated windows;
5. no fuzzy/edit-distance/morphological expansion.

If the 19 cases are heterogeneous, keep them unresolved and split narrower
follow-ups rather than introducing generic whitespace-insensitive matching.
