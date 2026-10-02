# #78 Plan: research -> TDD -> exact candidate expansion

## Gate 1 - research RED

Add pure audit helpers and tests before changing `alignment.py`.

RED contracts:

- parse exactly one balanced, non-nested parenthesis group into include/omit
  token candidates;
- reject nested/multiple/unbalanced parentheses and any expression mixed with
  slash or square brackets;
- parse exactly one token-internal slash into left/right candidates while
  preserving surrounding tokens;
- reject standalone slash, multiple slash tokens, empty branches, parentheses,
  and square brackets;
- aggregate only current exact-line lexical misses;
- distinguish unique rescue, ambiguous repeated-span rescue, multiple candidate
  rescues, and no rescue;
- aggregate payload contains no source strings or identifiers.

## Gate 2 - real-source evidence

Run the research audit on pinned Workbooks + reviewed CUC 0.2.8.

Record:

- eligible simple-parenthesis occurrence count;
- include-only / omit-only / both / ambiguous / none;
- eligible simple token-internal-slash occurrence count;
- left-only / right-only / both / ambiguous / none;
- excluded syntax-shape counts.

If the result does not support the hypothesized semantics, stop and revise the
research issue rather than implementing candidate expansion.

## Gate 3 - production RED

For each semantics class authorized by Gate 2, preserve production tests for:

- each independently evidenced branch;
- surrounding-token preservation;
- exact candidate match;
- two candidates matching distinct spans -> `AMBIGUOUS_HEADWORD_SPAN`;
- one candidate matching multiple spans -> ambiguity;
- no candidate matching -> `HEADWORD_NOT_FOUND`;
- unsupported syntax fails closed under the old behavior;
- plain and trailing-marker behavior unchanged;
- literal Burns headword remains stored verbatim.

## Gate 4 - implementation

Introduce a small headword-expression candidate layer in production alignment.
Do not add fuzzy matching, morphology, edit distance, or square-bracket
stripping.

The candidate layer returns ordered, de-duplicated token tuples. The aligner
unions exact CUC spans across candidates and resolves only when the union
contains exactly one span.

## Gate 5 - real source / module

Re-run pinned Workbooks acceptance and report the exact lexical coverage delta by
authorized syntax class. The feature-only Burns module may publish newly exact
word spans but must still emit no coarse line/tablet lexical fallback.

## Gate 6 - independent exact-head review

Review from the data-semantics boundary. Attack unsupported punctuation
generalization, candidate explosion, ambiguity collapse, privacy leakage, and
feature-only module regressions. Finalize only if exact-head unit, real-source,
reviewed-CUC/cfabric and other triggered gates are green.
