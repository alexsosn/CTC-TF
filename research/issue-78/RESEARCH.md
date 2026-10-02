# #78 Research: evidenced Burns headword-expression candidates

## Problem

The production aligner currently interprets one Burns `headword` as one literal
whitespace-token sequence (after NFC and trailing `*†!?` stripping) and compares
that tuple to one contiguous CUC `g_cons` window.

#77 established on pinned real Workbooks that this is not a general model of
Burns Column A:

- 4,039 resolved-line occurrences containing parentheses: 0 literal matches;
- 283 containing square brackets: 0 literal matches;
- 207 containing slash: 0 literal matches;
- clean and marker-only expressions each remain near 80% literal match.

#80 independently showed that ±1/±2 line drift is not the mass explanation:
4,869/4,993 current lexical misses have no exact neighbor-line hit.

The source schema contains no per-occurrence attested-form column. Candidate
surface forms therefore have to be inferred conservatively from the authored
headword expression and tested against the cited CUC line.

## Research boundary

This ticket may widen matching only for expression constructs whose semantics are
supported by source/data evidence. It must not introduce fuzzy matching,
stemming, morphology, edit distance, or arbitrary punctuation deletion.

Square brackets remain #79 because restoration has to be checked against CUC
editorial features.

## Phase A: source-safe empirical candidate audit

Before changing production alignment, evaluate two narrow hypotheses against the
same resolved CUC line using the unchanged exact `_candidate_spans()` matcher.

### One balanced parenthesized group

For an expression with exactly one balanced, non-nested parenthesized group and
no square brackets:

- `include_group`: remove only the parentheses, retaining the enclosed tokens;
- `omit_group`: remove the complete parenthesized group.

Example shape only:

```
A (B C) D
include_group -> A B C D
omit_group    -> A D
```

This is a research hypothesis, not yet a production grammar. Count separately:

- only include matches uniquely;
- only omit matches uniquely;
- both map to the same span;
- both map to distinct spans;
- one/both candidates are internally ambiguous on the cited line;
- neither matches.

Partition by #77 parenthesis position shape (leading/trailing/medial). Multiple,
nested, unbalanced, and bracket-bearing forms remain unsupported in this phase.

### Simple inline slash

Inventory slash syntax without source strings:

- number of slash-bearing whitespace tokens;
- standalone `/` token vs inline slash;
- multiple slash characters;
- overlap with parentheses/brackets.

For the first research matcher, only a headword with exactly one inline slash in
exactly one token, no parentheses, and no square brackets is eligible.

```
A B/C D -> {A B D, A C D}
```

Count left-only, right-only, both-same-span, both-distinct-span, ambiguous, and
neither. Do not interpret unsupported slash shapes.

## Evidence threshold

A production rule is justified only if:

1. the transform rescues substantial real-source occurrences on their cited
   line by exact CUC identity;
2. false ambiguity is explicitly measured;
3. the rule is syntactically bounded and deterministic;
4. no candidate is selected merely because it is the first generated match;
5. unsupported constructs fail closed.

A strong rescue association establishes operational semantics for alignment; it
does not prove a universal philological meaning for every punctuation mark.

## Production model if Phase A supports it

Introduce a parsed headword-expression layer returning labeled candidate token
sequences. The verbatim Burns `headword` remains unchanged for provenance and
public features.

The line resolver will:

1. generate a bounded ordered set of exact candidate token tuples;
2. run the existing exact contiguous CUC matcher for every candidate;
3. deduplicate identical spans reached by multiple candidates;
4. return exact lexical alignment only when the union contains exactly one span;
5. preserve explicit ambiguity when the union contains multiple spans;
6. keep `HEADWORD_NOT_FOUND` when no supported candidate matches.

Candidate labels are diagnostic/provenance, never confidence inflation.

## Out of scope

- square-bracket restoration (#79);
- morphology/tokenization/transcription residuals (#81);
- source-supported systematic line remapping (#85);
- fuzzy matching of any kind.


## Phase A real-source result

Pinned real Workbooks + reviewed CUC 0.2.8 on PR #87 provide a decisive
operational distinction between the two hypotheses.

### Simple parenthesized expressions

After excluding square-bracket overlap, slash overlap, multiple/nested groups,
and unbalanced forms, **3,458** current `HEADWORD_NOT_FOUND` occurrences are
eligible.

Per-candidate exact span cardinality:

| candidate | 0 spans | 1 span | 2+ spans |
|---|---:|---:|---:|
| include parenthesized group | 3,432 | 26 | 0 |
| omit parenthesized group | 422 | 2,928 | 108 |

Combined-hypothesis outcomes:

- unique omit-group rescue: 2,902;
- distinct include-vs-omit spans: 26;
- candidate ambiguity: 108;
- no match: 422;
- unique include-group rescue: **0**.

The 26 include-group matches therefore add no independent coverage at all: every
one occurs where omit-group also matches a different span. Treating the
parenthesized material as an optional surface candidate would create 26 extra
ambiguities without rescuing one additional occurrence.

**Production decision:** for the strictly supported one-group syntax, the only
evidenced surface candidate is the expression with the complete parenthesized
group omitted. The verbatim Burns headword remains preserved as provenance.
This is an operational alignment rule; it does not claim one universal
philological meaning for parentheses outside the supported class.

By position, unique omit-group rescues under the two-candidate research audit
were heavily represented in trailing groups (2,785), but also present for
leading (95) and medial (22) groups. Unsupported cases remain fail-closed:

- multiple/nested: 209;
- slash overlap: 90;
- square-bracket overlap: 277;
- unbalanced: 5.

### Simple inline slash

After excluding parenthesis overlap and complex multi-slash syntax, **35**
current misses are eligible.

Per-branch exact cardinality:

| candidate | 0 spans | 1 span |
|---|---:|---:|
| left branch | 18 | 17 |
| right branch | 27 | 8 |

Combined outcomes:

- unique left: 16;
- unique right: 7;
- distinct left-vs-right spans: 1;
- no match: 11;
- repeated-span ambiguity within one branch: 0.

**Production decision:** retain both branches as exact candidates. Deduplicate
the union by CUC span. One resulting span is exact lexical alignment; multiple
distinct spans remain `AMBIGUOUS_HEADWORD_SPAN`; zero remain
`HEADWORD_NOT_FOUND`.

Unsupported slash cases remain fail-closed:

- multiple slash characters: 28;
- parenthesis overlap: 144.

### Expected bounded coverage effect

The two production rules are disjoint in this ticket. On the current pinned
data they should move, before any #79 restoration work:

- at least 2,928 simple-parenthesis occurrences to exact lexical spans;
- 108 simple-parenthesis occurrences to explicit lexical ambiguity;
- 23 simple-slash occurrences to exact lexical spans;
- 1 simple-slash occurrence to explicit lexical ambiguity.

Thus exact lexical coverage should rise from 4,357 to **7,308** occurrences,
while these rules alone should reduce current `HEADWORD_NOT_FOUND` from 4,993
to **1,933** and increase ambiguous headword spans from 169 to **278**.

Those are acceptance expectations for the production TDD gate, not hard-coded
corpus constants in the matcher.


## Production verification

The bounded production implementation matches the Phase A prediction exactly on
the pinned Workbooks + reviewed CUC 0.2.8:

- exact lexical occurrences: **7,308** (previously 4,357);
- `HEADWORD_NOT_FOUND`: **1,933** (previously 4,993);
- ambiguous headword spans: **278** (previously 169).

The source-safe hypothesis audit is outcome-independent and reproduces the same
pre-production evidence after the matcher change.

Feature-only multiplicity expands accordingly:

- carrier/start words: **5,924**;
- exact occurrences: **7,308**;
- current maximum lane depth: **6**;
- span lengths: 1=6,653; 2=441; 3=206; 4=5; 5=3.

This confirms the #82 decision not to hard-code the earlier lane-2 maximum.
No new CUC nodes or warp files are introduced; newly exact occurrences flow
through the existing feature-only lane schema.
