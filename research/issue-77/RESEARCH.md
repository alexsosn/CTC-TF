# #77 Research: Burns headword-expression grammar audit

## Question

The current Burns→CUC aligner treats one Burns `headword` as one literal ordered token tuple after only NFC, whitespace splitting, and removal of trailing `*†!?`. That rule was deliberately conservative in #26, but it is not evidence that Burns Column-A headwords are literal diplomatic surface strings at every cited occurrence.

Issue #77 therefore reopens the lexical-coverage conclusion from #68 at the source-model boundary. This slice is **audit-only**: do not widen production matching yet.

## Existing evidence

The parsed Workbook schema contains `root`, `headword`, `ktu`, and `references`, but no separate field containing the attested surface form at each cited locus. Surface candidates must therefore be recovered from the cited CUC text under source-supported headword semantics.

The parser already:

- repairs the legacy transliteration font;
- applies a small documented set of headword corrections;
- preserves epigraphic brackets and punctuation;
- preserves trailing `*†!?`;
- treats `Not attested` separately as non-textual.

The aligner then strips only trailing `*†!?` from whitespace-separated headword tokens and requires exact contiguous equality to CUC `g_cons`.

A previous aggregate lexical-gap audit reported 4,993 `HEADWORD_NOT_FOUND` occurrences but classified only token count, exact-token overlap, and single-token prefix/suffix/containment. It did not classify authored punctuation/expression shapes.

## Hypotheses to reproduce, not assume

A separate analysis reported approximate classes such as parenthesized, bracketed, slash, marker-only, and clean headwords with sharply different match rates. Those values are not yet repository evidence. The real-source gate must independently reproduce or correct them.

The audit must be occurrence-based: one annotation can cite multiple targets, and lexical success/failure is an occurrence property.

## Safe aggregate model

Classify the verbatim Burns headword without emitting it.

Record independent boolean flags:

- `parentheses`: contains `(` or `)`;
- `square_brackets`: contains `[` or `]`;
- `slash`: contains `/`;
- `trailing_editorial_marker`: after whitespace tokenization, at least one token ends in `*†!?`;
- `unbalanced_parentheses`;
- `unbalanced_square_brackets`.

Also classify coarse parenthesis position shapes without lexical content:

- `none`;
- `leading`;
- `trailing`;
- `medial`;
- `whole_expression`;
- `multiple_or_nested`;
- `unbalanced`.

For comparison with the reported mutually exclusive table, define an explicit deterministic precedence rather than pretending classes do not overlap:

1. parenthesis-bearing;
2. square-bracket-bearing;
3. slash-bearing;
4. marker-only (editorial marker present and none of the preceding expression punctuation);
5. clean (none of the preceding flags).

This table is diagnostic only. Independent flag/signature counts remain authoritative for overlap.

## Match denominator

Only occurrences with an exact resolved CUC line are relevant to lexical expression matching:

- exact lexical `word_span` occurrences count as matched;
- `HEADWORD_NOT_FOUND` and `AMBIGUOUS_HEADWORD_SPAN` on an exact context line count as not uniquely matched;
- structural tablet-only targets, line-not-found, ambiguous-line, out-of-CUC, non-textual, and reference-parse failures are excluded.

This avoids conflating headword grammar with CUC coverage/reference grammar.

## Privacy boundary

Default/CI output must contain aggregate counts only. It must not emit:

- headword/root text;
- KTU/reference strings;
- source path/row/page;
- annotation/occurrence ids;
- CUC line content.

A local/private future diagnostic can show concrete examples, but this ticket does not need to commit or upload any Burns-derived strings.

## Decision boundary

This audit may show a strong association between syntax shape and literal-match failure. It does **not** by itself prove that every parenthesized group is optional/appositive, every slash is an alternative, or every bracket can be stripped. Those semantics require source/example research before #78/#79 production rules.

## Dependencies / follow-up

- #78 consumes only expression semantics established by this research.
- #79 handles square-bracket/restoration policy separately.
- #80 independently checks valid-but-shifted line addresses.
- #81 classifies residual clean failures only after expression/address fixes.
- #82 restores the feature-only CUC module architecture and must not depend on coarse line anchors as lexical annotations.


## Real-source result (PR #83)

Pinned real-source workflow `37000613682` on head `557b68720a16ce7b63ff66f1886317cfd0f7f261` passed against the checksum-pinned Workbooks and reviewed CUC 0.2.8.

The lexical-expression denominator is 9,519 exact-line occurrences:

- 4,357 exact lexical word-span matches;
- 4,993 `HEADWORD_NOT_FOUND`;
- 169 `AMBIGUOUS_HEADWORD_SPAN`.

### Independent punctuation flags

| authored shape flag | occurrences | exact matches | not found | ambiguous span |
|---|---:|---:|---:|---:|
| parentheses | 4,039 | 0 | 4,039 | 0 |
| square brackets | 283 | 0 | 283 | 0 |
| slash | 207 | 0 | 207 | 0 |
| trailing `*†!?` marker | 2,200 | 1,656 | 451 | 93 |

The zero-match association for parentheses, brackets, and slash is therefore reproduced on the actual source. The previously reported raw counts are **not** reproduced literally because these flags overlap.

### Exact syntax signatures

The overlap is material:

- `parentheses`: 3,604
- `parentheses+marker`: 68
- `parentheses+slash`: 77
- `parentheses+slash+marker`: 13
- `parentheses+square_brackets`: 223
- `parentheses+square_brackets+slash`: 26
- `parentheses+square_brackets+slash+marker`: 28
- `slash`: 45
- `slash+marker`: 18
- `square_brackets`: 5
- `square_brackets+marker`: 1
- `marker`: 2,072
- `clean`: 3,339

Thus 277/283 square-bracket occurrences also contain parentheses, and 144/207 slash occurrences also contain parentheses. A single precedence-based bucket can conceal this structure.

### Parenthesis position

All 4,039 parenthesis-bearing occurrences fail literal matching. Their source-safe structural shapes are:

- trailing group: 3,523
- leading group: 143
- medial group: 82
- multiple/nested: 286
- unbalanced: 5
- whole-expression: 0

The dominance of trailing `X (...)` structure is strong evidence that literal punctuation is not an appropriate surface-span representation. It is **not**, by itself, proof that every parenthesized group has one uniform optional/appositive semantics. #78 must establish candidate-expansion semantics from source evidence and real cited-line behavior before production widening.

### Editorial marker evidence

Marker-bearing occurrences do not share the zero-match behavior. The exact aggregate marker signatures are:

- `*`: 238 occurrences, 156 exact matches
- `*†`: 1,543, 1,231 exact matches
- `†`: 268, 197 exact matches
- `*!`: 41, 28 exact matches
- `*†!`: 92, 40 exact matches
- `†!`: 16, 4 exact matches
- `!`: 2, 0 exact matches

No trailing `?` signature occurs in this eligible lexical denominator. The exclusive marker-only class has 2,072 occurrences and 1,656 exact matches (~79.9%); the clean class has 3,339 and 2,701 exact matches (~80.9%). This confirms that the documented stripping of trailing editorial markers is not the dominant lexical-gap defect.

## Research conclusion

The real-data evidence rejects the use of one literal headword token tuple as a general model of Burns Column A. Parentheses, square brackets, and slash correlate perfectly with current exact-match failure, while clean and marker-only expressions match at roughly the same ~80% rate.

This ticket does **not** authorize stripping punctuation or generating lexical entities from guessed alternatives. It establishes the expression inventory and isolates the next questions:

- #78: source-supported parenthesis/slash candidate semantics;
- #79: restoration-aware square-bracket semantics;
- #80: independent address/line-drift audit;
- #81: residual clean/marker-only failures after those corrections.

The previous #68 conclusion that exact-contiguous matching is already an adequately researched final lexical boundary is therefore too strong and should not be used as a release-completeness claim.
