# #97 Research: one-edit Burns↔CUC transcription/orthography residuals

## Starting evidence

#81 identifies 112 clean/marker-only residual occurrences whose cited line has
one unique CUC word at Levenshtein distance 1 after higher-priority neighbor,
exact-boundary and containment evidence is excluded:

- deletion relation: 52;
- substitution: 47;
- insertion: 13.

Edit distance is diagnostic only. It is not an alignment rule.

## Research questions

For exactly that 112-occurrence hierarchy class, aggregate:

- substitution source→CUC code-point pairs;
- inserted CUC code points and start/internal/end positions;
- deleted Burns code points and start/internal/end positions;
- Unicode code-point identity after NFC;
- whether any operation involves a combining mark;
- distinct Burns annotation counts / occurrence multiplicity;
- workbook and worksheet-role concentration.

Use code-point labels such as `U+1E6F>U+0074` rather than lexical strings.

## Operation semantics

The direction is Burns candidate → CUC surface word.

- substitution: same length, one source code point replaced by one CUC code point;
- insertion: CUC has one additional code point;
- deletion: CUC has one fewer code point.

The implementation must derive the unique edit script only after confirming
Levenshtein distance exactly 1.

## Evidence boundary

CI/committed output contains aggregate code-point/position counts only. Never
emit Burns/CUC words, locators, rows, ids, or CUC nodes.

Concrete examples remain local/private.

## Production gate

No generic edit-distance matcher.

Only a recurrent confusion independently demonstrated to be an actual
transliteration/parser convention may become a deterministic normalization
rule, with a dedicated TDD ticket and negative controls.
