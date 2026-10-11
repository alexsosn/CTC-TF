# #77 Plan: source-safe headword-expression audit

## Gate 1 — RED contract

Add unit tests for a pure source-safe classifier and aggregate occurrence cross-tab before production implementation exists.

Required RED cases:

1. parenthesized expression is classified without exposing lexical text;
2. bracket/slash/marker flags are independent and overlaps are retained;
3. mutually exclusive comparison bucket uses documented precedence;
4. unbalanced delimiters are visible rather than silently normalized;
5. lexical match accounting distinguishes exact `word_span` from `HEADWORD_NOT_FOUND` on the same resolved line;
6. tablet-only/unresolved/non-textual cases do not enter the lexical-expression denominator;
7. serialized aggregate payload contains no source strings.

## Gate 2 — GREEN implementation

Implement only pure audit helpers in `scripts/audit_burns_alignment.py`:

- `classify_headword_expression(headword)`;
- `aggregate_headword_expression_stats(source, alignments)`.

Do not modify `_headword_tokens`, `_candidate_spans`, reference resolution, or TF publication.

Add the aggregate result to `scripts/check_real_burns_source.py` so the existing pinned real-source workflow supplies evidence.

## Gate 3 — real source

Run the existing real Workbooks acceptance workflow against:

- pinned Workbooks source;
- reviewed CUC 0.2.8;
- the branch implementation.

Record aggregate shape counts and match rates in this research directory / issue comment after the run. Do not copy source strings from logs or local artifacts.

## Gate 4 — interpretation

Compare the observed result to the reported hypotheses. Explicitly separate:

- measured association (e.g. punctuation class vs literal match);
- unproven philological semantics (e.g. optionality/apposition/alternative reading).

If the data expose an additional structurally distinct class, create a child issue rather than broadening #77 silently.

## Gate 5 — review

Perform a logically independent adversarial review of the exact final PR head. Review should attack:

- denominator leakage from structural/reference failures;
- overlapping flags hidden by exclusive buckets;
- source-string privacy leaks;
- accidental production matching changes;
- unsupported semantic claims derived only from punctuation.

Only finalize #77 if the exact-head tests and real-source workflow are green and the review finds no blocker.
