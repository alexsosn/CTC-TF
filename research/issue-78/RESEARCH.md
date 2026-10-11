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


## Real-source evidence

Pinned Workbooks + reviewed CUC 0.2.8 on PR #88, research head
`6d826b4b284440b13075cc8727ef9dae0ab64d3b`, passed the unit and real-source
gates.

### Simple single-parenthesis expressions

3,357 current `HEADWORD_NOT_FOUND` occurrences satisfy the conservative simple
single-parenthesis grammar.

Exact cited-line cardinality:

- core (parenthesized group omitted): 2,873 unique, 105 repeated/ambiguous, 379 absent;
- expanded (parentheses removed but contents retained): 23 unique, 0 repeated, 3,334 absent.

Joint outcomes:

- core only: 2,850;
- core + expanded: 23;
- expanded only: **0**;
- ambiguous: 105;
- neither: 379.

This is stronger than the original optional-candidate hypothesis. No real
occurrence in this simple class requires the expanded expression to obtain an
exact match. Every observed expanded exact match already coexists with an exact
core match. The production rule authorized by this evidence is therefore:

> For the narrowly parsed simple-parenthesis class, the lexical anchor candidate
> is the **core with the parenthesized group omitted**, not a union of core and
> expanded spans.

This remains conservative: 105 repeated core spans become explicit lexical
ambiguity and 379 cases remain unresolved. Mixed, nested, unbalanced and
square-bracket syntax is not normalized by this rule.

### Simple token-internal slash expressions

35 current `HEADWORD_NOT_FOUND` occurrences satisfy the conservative
token-internal single-slash grammar.

Exact cited-line outcomes:

- left only: 16;
- right only: 7;
- both branches: 1;
- neither: 11;
- repeated-span ambiguity: 0.

Independent cardinality gives 17 unique left-branch matches and 8 unique
right-branch matches. Both branches are therefore genuinely attested across the
cited source lines. The production rule authorized for this narrow syntax class
is an ordered, de-duplicated **left/right alternative candidate set**.

When both alternatives yield different exact spans, the result must remain
`AMBIGUOUS_HEADWORD_SPAN`; no branch preference is justified.

### Coverage implication before implementation

Without changing any other syntax class, the evidence authorizes up to:

- 2,873 newly exact simple-parenthesis occurrences;
- 23 newly exact simple-slash occurrences;
- 106 additional explicit ambiguous-span occurrences (105 parenthesis core
  repetitions + 1 line matching both slash branches).

The production run, not this arithmetic projection, is authoritative because it
must re-run the complete deterministic alignment and module gates.

## Decision

Gate 2 is satisfied for exactly two syntax classes:

1. one balanced, non-nested parenthesized group, not mixed with slash or square
   brackets: use the core candidate only;
2. one token-internal slash, not mixed with parentheses/square brackets: use both
   branches as exact alternatives.

Everything else fails closed and is left for #79 or follow-up research. No fuzzy,
morphological or edit-distance matching is authorized by this issue.
