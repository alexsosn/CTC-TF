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
