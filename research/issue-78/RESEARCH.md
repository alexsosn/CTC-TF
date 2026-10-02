# #78 Research: evidence for Burns headword candidate semantics

## Problem

The production aligner currently interprets a Burns `headword` as one literal
whitespace-token sequence (after NFC and documented trailing `*†!?` removal).
#77 demonstrated on the pinned real Workbooks that this model fails
systematically for authored expression punctuation:

- 4,039 parenthesis-bearing exact-line occurrences: 0 literal matches;
- 283 square-bracket occurrences: 0 literal matches;
- 207 slash occurrences: 0 literal matches;
- marker-only and clean expressions both retain roughly 80% literal-match rates.

That establishes a parser/model defect, but not the semantics of any punctuation.

## Source boundary

The Workbook schema contains no separate attested-form column. The source gives
a headword/grouping expression plus cited KTU loci; the attested surface must be
recovered from the cited text.

The White Rose deposit describes the Workbooks as the database accompanying
Burns's thesis, but the publicly searchable thesis metadata/text available to
this research does not expose an explicit legend defining every use of
parentheses or slash. Therefore this ticket must not promote punctuation-based
guesses directly into production.

Square brackets remain out of scope here and belong to #79.

## Research strategy

Use the cited CUC line itself as an independent behavioral check for narrowly
defined, structurally simple expression classes.

### Simple single-parenthesis expressions

For a balanced expression containing exactly one non-nested parenthesized group,
with no square brackets and no slash, compare two exact candidate readings:

1. **include**: remove only the literal parentheses and retain their contents;
2. **omit**: remove the parenthesized group and its contents.

After that structural transformation, apply only the existing documented
headword token normalization (NFC, whitespace tokenization, trailing
`*†!?` removal) and exact contiguous matching against CUC `g_cons`.

Record whether the cited line supports include only, omit only, both, neither,
or an ambiguous repeated span. Do not change production alignment.

If both include-only and omit-only readings occur across independently cited
real occurrences in substantial numbers, that is direct source-use evidence
that the parenthesized group is not literal mandatory surface text and that a
bounded candidate set can model at least this simple class.

### Simple token-internal slash expressions

Treat only expressions with exactly one slash inside one whitespace token and no
parentheses/square brackets. Replace that token with the left branch and right
branch separately while preserving all surrounding tokens.

Record left-only, right-only, both, neither, or ambiguity using exact CUC
matching. Do not yet interpret standalone slash tokens or multiple slashes.

If both branches are independently attested across cited lines, that supports an
alternative-reading candidate rule for this narrow class. Other slash shapes
remain unsupported and fail closed.

## Safety / privacy

Committed and CI output is aggregate-only. Never emit Burns headwords, KTU
locators, source rows/pages, CUC line strings, annotation IDs, occurrence IDs,
or node IDs.

A developer may inspect examples locally from the licensed source, but no
source-derived example corpus is committed or uploaded.

## Decision rule

Production expansion in #78 is authorized only for a syntax class where:

1. parsing is structurally unambiguous;
2. real cited-line evidence demonstrates the proposed alternatives;
3. candidate generation is finite and deterministic;
4. exact matching remains the final lexical criterion;
5. multiple matching candidates/spans remain explicit ambiguity.

Unsupported, nested, mixed punctuation and square-bracket expressions stay
unresolved rather than being normalized heuristically.
