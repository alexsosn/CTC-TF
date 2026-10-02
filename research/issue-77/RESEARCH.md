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
