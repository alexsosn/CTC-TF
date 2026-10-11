# #96 Research: Burns single-token containment residuals

## Starting evidence

The #81 pinned-Workbooks classifier isolates **108** clean/marker-only
`HEADWORD_NOT_FOUND` occurrences with exactly one containing CUC word on the
cited line after higher-priority neighbor and exact token-boundary evidence:

- Burns token is a prefix of the CUC word: **64**;
- Burns token is a suffix of the CUC word: **41**;
- Burns token is strictly internal: **3**.

Containment is diagnostic only. It does not establish a lemma/form relation or
authorize affix stripping.

## Research questions

For exactly this hierarchy class, measure source-safe structure:

- extra CUC code-point count on the left/right of the Burns token;
- left-only / right-only / both-side extras;
- individual extra code-point frequencies by side;
- one-code-point vs multi-code-point extras;
- distinct Burns annotation counts and occurrence multiplicity;
- workbook and worksheet-role concentration;
- repeated containing-word ambiguity excluded from the unique class.

The direction is always Burns candidate -> cited CUC surface word.

## Morphology boundary

CUC 0.2.8's reviewed production contract provides `g_cons`, but no reviewed
lemma/root/morphology layer. String containment alone must not be reinterpreted
as morphology.

A recurrent extra consonant is only a hypothesis (clitic, affix, citation-form
difference, proper-name spelling, parser artifact, etc.) until concrete
Workbooks/CUC examples are inspected locally and an explicit lexical or
morphological source supports the relation.

If DULAT or another lexical/morphological dependency is introduced, it must be
reviewed and fingerprinted as a separate dependency rather than used as an
implicit heuristic.

## Evidence/privacy boundary

CI and committed research output may contain only aggregate counts, code-point
labels (`U+....`), lengths, workbook numbers and generic worksheet roles.

Never emit Burns headwords, CUC words, KTU locators, source rows/pages, ids, or
CUC node ids. Concrete examples stay local/private.

## Production gate

No prefix/suffix stripping and no substring matcher.

Only a separately evidenced deterministic morphology/orthography rule may enter
production, with ambiguity controls and its own RED/GREEN real-source slice.
