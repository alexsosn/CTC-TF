# #81 Research: residual clean/marker lexical misses

## Denominator after expression fixes

After #78, #79 and #90, expression-syntax failures are explicitly separated
from the morphology/tokenization problem.

Pinned real Workbooks currently have 1,841 `HEADWORD_NOT_FOUND` occurrences,
but #81 is intentionally restricted to the authored shapes whose lexical text
is already understood by production tokenization:

- clean headwords: **562** misses;
- marker-only headwords: **323** misses;
- total clean/marker denominator: **885**.

Parenthesis, slash, square-bracket, mixed and malformed expression syntax stays
outside this ticket.

## Address evidence before morphology

The candidate-aware #91 ±1/±2 audit finds among those 885:

- clean: 80 unique-neighbor, 9 multi-neighbor, 473 no-neighbor;
- marker-only: 30 unique-neighbor, 5 multi-neighbor, 288 no-neighbor.

Thus **124/885** clean/marker misses already have exact neighboring-line
evidence. These must be classified as address/segmentation suspects before any
morphological interpretation.

The morphology/tokenization-oriented current-line population is therefore at
most **761** occurrences.

## Existing normalization boundary

The Workbook parser already repairs the documented legacy-font transliteration
characters and a small explicit typo list. Alignment then uses NFC, whitespace
tokens and removal of trailing `*†!?`. Reviewed CUC 0.2.8 supplies `g_cons`
but no reviewed lemma/root/morphology feature in the current compatibility
contract.

Therefore this research first measures string/token structure. It does not infer
lemmas or silently consult an unreviewed lexicon.

## Source-safe structural probes

For each clean/marker-only `HEADWORD_NOT_FOUND` occurrence:

1. **neighbor evidence** — using the same production candidate semantics and
   ±1/±2 structural boundary as #91;
2. **token-boundary exactness** — concatenate the Burns tokens and every
   contiguous CUC word window; an exact character sequence with different word
   boundaries is a split/merge signal, not fuzzy matching;
3. **exact-token order** —
   - all Burns tokens occur in order but non-contiguously;
   - all occur but only reordered;
   - partial exact-token overlap;
   - zero exact-token overlap;
4. **single-token containment** — unique/multiple CUC words where the Burns token
   is an exact prefix, suffix or internal substring;
5. **single-token edit distance** — minimum Levenshtein distance to CUC words on
   the cited line, with a separate count for a unique distance-1 candidate;
6. aggregate by workbook number and worksheet role, without source labels,
   locators, rows, ids or lexical strings.

These are diagnostic features. They are not production match rules.

## Classification hierarchy

For an occurrence-level summary, use a deterministic mutually-exclusive
hierarchy:

1. neighbor evidence;
2. exact token-boundary-only match on the cited line;
3. all tokens in order but non-contiguous;
4. all tokens present but reordered;
5. unique single-token containment/affix-like candidate;
6. unique single-token edit-distance-1 candidate;
7. partial exact-token overlap;
8. no exact-token overlap;
9. other.

The hierarchy is only for accounting; orthogonal counters remain authoritative.

## Production gate

No production widening is allowed from aggregate similarity alone.

Any proposed rule must become its own evidence-backed TDD slice. Examples:

- a deterministic CUC/Burns token split/merge convention may be eligible if
  repeated and semantically exact;
- an affix-like string relation is **not** enough to call a lemma/form mapping;
- edit distance is diagnostic only unless a specific transcription convention
  is independently established;
- morphology requires an explicit reviewed lexical/morphological dependency,
  not heuristic stemming.

## Private diagnostic

A local-only detailed report may contain Burns headword, cited CUC line,
candidate operations and source provenance when explicitly requested. Such a
report must never be printed by CI, committed, uploaded, or included in the
public TF module.
