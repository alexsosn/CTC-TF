# #78 Plan: research -> candidate grammar -> TDD -> real data -> review

## Gate 1 - research RED

Preserve tests for pure research helpers before implementation:

- one simple trailing parenthesized group emits include/omit hypotheses;
- leading and medial groups preserve authored token order;
- multiple/nested/unbalanced parentheses fail closed;
- square brackets exclude the parenthesis research rule;
- exactly one inline slash token emits two branch candidates;
- standalone slash, multiple slash tokens/characters, parentheses, and brackets
  remain unsupported by the first slash hypothesis;
- candidate output is bounded, deterministic, deduplicated, and never contains
  Burns/KTU identifiers beyond the candidate token tuples supplied by the test.

Add a source-safe aggregate audit over current `HEADWORD_NOT_FOUND` occurrences.
Committed/CI output contains counts and static labels only.

## Gate 2 - pinned real Workbooks

Run the audit against pinned Workbooks + reviewed CUC 0.2.8.

Record:

- eligible/unsupported counts by expression shape;
- exact rescue counts per candidate;
- same-span vs distinct-span double matches;
- candidate-level ambiguous spans;
- no-match remainder.

Do not change production alignment until these results support a bounded rule.

## Gate 3 - production RED (only if Gate 2 supports it)

Introduce tests around `align_burns_annotation` / line resolution for supported
constructs:

- parenthesized group present;
- parenthesized group absent;
- slash left branch;
- slash right branch;
- two candidates converging on one span remains exact;
- two candidates yielding distinct spans becomes
  `AMBIGUOUS_HEADWORD_SPAN`;
- unsupported expression remains `HEADWORD_NOT_FOUND`;
- plain and trailing-`*†!?` behavior is unchanged;
- verbatim headword storage is unchanged.

## Gate 4 - GREEN implementation

Add a small parsed/candidate expression layer. Keep `_candidate_spans()` exact
and unchanged where possible. Do not add morphology/fuzzy behavior.

## Gate 5 - downstream real-data verification

Rerun:

- unit matrix;
- pinned real Workbooks feature-only acceptance;
- reviewed CUC + cfabric-mcp feature-only module;
- Context-Fabric compatibility;
- other path-triggered repository acceptance workflows.

Report before/after exact lexical coverage by expression class. Newly resolved
occurrences must flow through the already-correct feature-only module as exact
word lanes; unresolved/ambiguous cases remain report-only.

## Gate 6 - logically independent exact-head review

Attack:

- over-broad punctuation stripping;
- candidate explosion;
- first-match selection;
- accidental bracket/restoration handling;
- ambiguity collapse;
- changed plain-headword behavior;
- candidate rules justified only by synthetic tests rather than real Workbooks;
- new exact matches landing on structural nodes;
- report/TF provenance divergence.

Do not finalize if any blocker remains.
