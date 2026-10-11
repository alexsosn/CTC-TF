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


## Real-source aggregate result

Pinned Workbooks + reviewed CUC on exact GREEN head
`f90c7fc75000235e8589f2bbb6ccace1dba61132` reproduce the #81 family exactly:

- clean/marker residual denominator: **885**;
- exact-concatenation boundary occurrences: **19**;
- unique current-line candidate windows: **19/19**;
- distinct Burns annotations represented: **16**;
- one occurrence also has a unique neighboring-line exact candidate.

Occurrence multiplicity by annotation:

- 14 annotations contribute one boundary occurrence;
- 1 annotation contributes two;
- 1 annotation contributes three.

Thus the family is not an artifact of one highly repeated Burns label.

### Direction

Burns-token → CUC-word boundary direction:

- split: **14**;
- merge: **5**;
- resegment at equal token count: **0**.

Token-count transitions:

- 1→2: 2;
- 2→1: 2;
- 2→3: 2;
- 3→2: 3;
- 3→4: 10.

The dominant length signature is
`4,2,4 -> 4,2,1,3`: **7 occurrences from 4 distinct annotations**.
This is repeated independent structural evidence, but length signatures alone
do not identify the linguistic boundary or prove that a generic rule is safe.

### Empty CUC consonantal words

Three of the 19 exact-concatenation windows contain a CUC word whose
`g_cons` is empty. Their signatures are:

- `2,3,4 -> 2,3,0,4`;
- `3,1,3 -> 3,1,0,3`;
- `3,4 -> 3,0,4`.

These are not ordinary consonantal split evidence and must be inspected
separately before any production rule can use them.

## Decision

The aggregate evidence is strong enough to justify local inspection of a
recurrent segmentation family, especially the four independent annotations
behind `4,2,4 -> 4,2,1,3`.

It is **not** sufficient to add generic whitespace-insensitive production
matching. Concrete local examples are still required to establish whether the
recurrent patterns are clitic/word segmentation conventions, source grouping,
or parser/textual artifacts.

Production remains unchanged in this research PR.
