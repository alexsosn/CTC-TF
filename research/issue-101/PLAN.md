# #101 Plan: empty-g_cons research slice

## RED tests

Use synthetic CUC structural fixtures whose empty-`g_cons` words still own sign slots:
1. exact concatenation window with an internal empty CUC word; measure its one-based generic position, sign-slot cardinality and aggregate sign/editorial-feature presence;
2. windows without empty CUC words do not contribute;
3. repeated references count occurrences but do not inflate distinct Burns annotations or unique CUC empty words;
4. an empty word with missing/empty sign extent must raise rather than synthesize a fake sign;
5. JSON aggregate contains no Burns/CUC lexical strings, source IDs, KTU or word/sign node IDs.

The absence of this function in master should be the causal RED.

## GREEN

Implement diagnostic-only `aggregate_empty_g_cons_boundary_research()` in the research audit. Enumerate exact concatenation boundary windows using the existing helper. Record only structural histograms / presence, and distinguish the overall empty CUC population from the exact-window subset.

## Pinned real source and consistency

Use already-loaded fingerprinted `sign`, `emen`, `cert`, `alt` maps. Check the new `occurrences_with_empty_g_cons` and `windows_with_empty_g_cons` against #95's existing independent counters (expected 3 each). Include counts in source-safe `real_burns_audit`.

## Review and finalization

Review exact diff and real data independently for false 'blank word equals punctuation' assumptions, slot extent correctness, untrusted external text, repeated-reference inflation, source leakage and production alignment widening. Finalize only on green exact-head unit/real-source CI. Any linguistic rule needs another dedicated issue.
