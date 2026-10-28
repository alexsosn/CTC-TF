# #136 Research: empty-g_cons windows hidden by early exact-concatenation break

## Verified source defect

`scripts/audit_burns_alignment.py::_token_boundary_spans` concatenates CUC `word_g_cons` values in consecutive word windows and compares against Burns candidate tokens. On the first equality for each start, the inner loop `break`s regardless of whether following CUC words have empty `g_cons`.

The result is not a complete enumeration of equal-consonant *word windows*: adjacent zero-consonant words preserve concatenation but lead to distinct contiguous spans. For example, Burns `ab cd` over CUC `ab, cd, ''`: the exact baseline two-token window is excluded, but the longer three-word diagnostic window is missed. More generally, `ab, '', cd, ''` can produce two different windows from the same starting point, and a leading empty word permits an additional start. This skews `aggregate_token_boundary_research` cardinality, and `aggregate_empty_g_cons_boundary_research` misses additional positional/word evidence.

The existing #95 and #101 research used this helper; the documented 19 boundary occurrences and 3 empty-word windows are historical measurements and might change, not proven immutable facts. #101 already found 528 CUC empty-g_cons words with populated sign extents; source semantics remain unknown and an empty CUC word must **not** be treated as transparent for production lexical matching.

## Scope and adversarial constraints

Change only source-safe audit enumeration, not any Text-Fabric published feature or word-span alignment. Each contiguous (start,end) window is a distinct *diagnostic* possibility even with the same consonant string; exact token-equality windows remain excluded, and no window is output with raw words, strings, slots, or KTU locators. Keep all-zero word windows bounded and avoid accidental quadratic copies beyond the existing nested loop. Preserve a RED unit-test commit, then GREEN and real private Workbooks/CUC acceptance.

Potential issue: enumeration may reveal previously hidden ambiguity and change old counts. That is a correction, not license to coerce outputs back to historical values.
