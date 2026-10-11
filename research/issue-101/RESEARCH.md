# #101 Research: zero-consonant CUC words in token-boundary evidence

## Provenance and starting evidence

#95's pinned Workbooks/CUC-0.2.8 research found 19 clean/marker-only HEADWORD_NOT_FOUND occurrences with exact concatenated CUC word windows. All 19 windows were unique on their cited lines, but **three** contain at least one CUC word with an empty `g_cons`. Existing source-safe signatures are `2,3,4 -> 2,3,0,4`, `3,1,3 -> 3,1,0,3` and `3,4 -> 3,0,4`. Those windows depend on the empty word contributing zero consonants; they are not evidence for safe transparent lexical skipping.

## Model and scope

CUC `g_cons` is a word-level transcription feature, while `word_slots` in the reviewed CUC index exposes sign-node extents. The real Workbooks runner already loads CUC sign-level `sign`, `emen`, `cert`, and `alt` features under a fingerprinted editorial context. We can compare aggregate structural **presence** of these features on the signs of empty CUC words, including all empty CUC words outside the three cited windows, without exposing text.

The allowed aggregate measures are:
- total CUC words with empty `g_cons`, sign-slot extent-size histogram, and how many are cited in exact-boundary windows;
- candidate-window/occurrence counts with one or more empty CUC words, distinct Burns annotation counts, window word-position of each empty CUC word;
- for both the full empty-word population and the boundary subset: counts of sign slots with present `sign`, `emen`, `cert`, `alt`, and word-level any-sign/any-editorial presence;
- no CUC word/sign nodes, Burns headwords, KTU locators, lexical strings, feature values, or source rows in printed/committed output.

## Pinned real Workbooks result

Run `38050368757` (Real Burns Workbooks feature-only acceptance) **passed**
on audit head `e5fb22d1f95f9df9b86dad817d36cb6fd9f68066`,
using reviewed CUC 0.2.8. The counts reported here are aggregate only.

- The CUC base contains **528** words whose `g_cons` is empty.
- All 528 have at least one populated `sign` on their sign extent;
  **490/528** have at least one populated `emen`; **0/528** have a
  populated `alt` or `cert` on those sign extents.
- Exactly **3/19** Burns boundary occurrences/windows contain an empty CUC
  word, reconciling both new counters with the previously independent #95
  counts. They represent **3 distinct Burns annotations** and **2 distinct
  empty CUC word nodes**, both with single-sign extents.
- In all three matched boundary windows, the empty word is in a **middle**
  position. Both underlying sign extents contain `sign` but lack populated
  `emen`, `cert`, and `alt`.
- Thus at least one of these two CUC words participates in more than one
  Burns occurrence; **3 occurrences do not imply 3 independent empty words**.

The fact that most CUC empty-`g_cons` words have editorial `emen`
presence, but these two do not, helps prioritize *local/private* source
inspection. It does **not** identify the two signs or authorize skipping them.
In particular, lexical alignment must remain conservative regardless of
whether `sign` is present.

Limit: the probe enumerates exact-concatenation windows through the same
`_token_boundary_spans` helper as #95. It independently measures the
empty-word identities and sign extents but does not enumerate arbitrary
zero-consonant words immediately adjacent to windows that #95 does not
classify. The three cases are the current #95 family, not necessarily all
possible CUC empty-word adjacency patterns.

## Why editorial presence is only a probe

The meaning of CUC `alt`, `emen` and `cert` and the values stored under them require source-level interpretation. A nonempty sign feature, or an empty consonantal transcription, does not establish whether the word is punctuation, a damaged sign, segmentation artifact, lacuna, or a lexical word. Even the combined aggregate cannot authorize skipping that word during lexical matching.

## Process and boundary

- Research and plan before implementation.
- Preserve synthetic RED for zero-consonant CUC word positions, sign-slot presence and repeated Burns-reference inflation; fail closed on missing sign extents.
- GREEN: separate diagnostic aggregate; do **not** touch production alignment, `headword_candidates`, or TF writer.
- Pinned Workbooks gate: reconcile empty-window/occurrence counts exactly against #95's existing boundary statistics.
- Perform independently reasoned exact-head review after CI; keep individual source forms local/private.

Decision: No transparent-empty-word lexical rule without separate philological review of the three local cases.
