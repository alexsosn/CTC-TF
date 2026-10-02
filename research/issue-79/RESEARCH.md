# #79 Research: restoration-aware square-bracket alignment

## Problem

Burns square brackets are editorial restoration markup, not consonants. The
historical literal matcher therefore cannot match bracket-bearing headwords.
Blindly deleting brackets is not acceptable: a published lexical span must be
supported by the cited CUC reading **and** by CUC's independently encoded
editorial evidence.

After #78 the remaining square-bracket population is still structurally mixed:
the #77 audit found 283 bracket-bearing exact-line occurrences, of which 277
also contain parentheses. Restoration handling must therefore be compositional;
supporting only a standalone `[word]` syntax would address almost none of the
real source.

## Reviewed CUC editorial model

At the exact reviewed base
`DT-UCPH/cuc@ad69400f5446e1c8217af01659c7c10ab00c015b`, the upstream README
defines:

- `g_cons`: consonantal representation of each **word**;
- `sign`: consonantal letter on **sign** nodes;
- `emen`: sign-level emendation, explicitly including reconstructed, missing,
  excised, or redundant signs/letters;
- `cert`: sign-level textual certainty (corresponding to KTU italics);
- `alt`: alternative reading.

The TF 0.2.8 files confirm `emen.tf`, `cert.tf`, and `alt.tf` are node
features; `emen` contains the value `restored`. Therefore restoration
agreement can be tested against the exact sign slots already owned by CUC.

## Research questions

1. Do CUC word `oslots` and sign values permit a stable character-by-character
   mapping from `g_cons` to the signs of words relevant to Burns?
2. For Burns bracketed characters, does CUC mark the corresponding sign(s)
   `emen=restored`?
3. How often does CUC mark additional signs restored that Burns leaves
   unbracketed?
4. Do `cert` or `alt` occur on otherwise restoration-compatible spans often
   enough that they need a separate fail-closed policy?
5. In mixed parenthesis+bracket expressions, are brackets entirely inside the
   parenthesized material already omitted by the evidenced #78
   `parenthesis_core` rule, or do they survive in the lexical core?
6. Which multiword / partial-word bracket shapes can be mapped exactly, and which
   must remain unresolved?

## Conservative bracket parser

Research parsing may remove square-bracket delimiters only after proving they are
balanced. It must retain, for every resulting token, the exact character
positions that were bracketed.

Reject at least:

- unbalanced brackets;
- nested brackets;
- empty bracket groups;
- bracket delimiters that cannot be mapped to lexical characters after existing
  trailing `*†!?` handling.

The parser must support brackets spanning part of a token, a whole token, and
multiple tokens. It does not itself authorize alignment.

## Compositional research

For a balanced bracketed expression:

1. remove only square-bracket delimiters while retaining a restoration mask;
2. apply the already-reviewed #78 candidate grammar to the debracketed
   expression;
3. carry the restoration mask through the selected candidate:
   - literal candidate: all surviving tokens retain their masks;
   - `parenthesis_core`: masks inside the omitted group disappear; masks on
     surviving core text remain requirements;
   - slash composition is measured separately and remains unsupported until its
     branch-mask semantics are shown unambiguous;
4. exact-match the candidate against the cited CUC `g_cons`;
5. map candidate characters to CUC word sign slots;
6. compare Burns bracketed positions with CUC `emen=restored`.

## Evidence classes

Aggregate-only research should distinguish at least:

- no exact debracketed lexical span;
- repeated/ambiguous exact span;
- sign sequence cannot be reconciled with `g_cons`;
- exact restoration agreement;
- Burns-restored position missing in CUC;
- extra CUC-restored position outside Burns brackets;
- both missing and extra restoration evidence;
- restoration-compatible span with CUC `cert` evidence;
- restoration-compatible span with CUC `alt` evidence;
- brackets entirely removed by `parenthesis_core` and therefore irrelevant to
  the selected lexical core.

No source strings, locators, node ids, or Burns identifiers may enter committed
or CI output.

## Production decision rule

A bracket rule may enter production only when:

- the bracket syntax is structurally deterministic;
- the debracketed reading matches exactly in the cited CUC line;
- every Burns-restored character surviving in the selected lexical candidate
  maps to a CUC sign carrying restoration evidence;
- any additional CUC restoration/certainty/alternative evidence is handled by
  an explicit reviewed policy rather than silently ignored;
- ambiguity remains ambiguity.

A bracket group lying entirely inside material already omitted by the reviewed
`parenthesis_core` rule does not need to assert a restoration reading, because
none of its characters are part of the lexical anchor.

## Compatibility / trust boundary

The current reviewed-CUC fingerprint contract protects the six structural files
needed before #79. Production use of `sign.tf`, `emen.tf`, `cert.tf`, or
`alt.tf` requires extending the reviewed file fingerprint manifest before
those files may influence published alignment. Research CI may inspect them
because the workflow checks out the exact pinned upstream commit, but that does
not substitute for the production local-file trust gate.


## Real-source result

Pinned Workbooks + reviewed CUC 0.2.8 were audited before production widening.

All 283 square-bracket-bearing resolved-line occurrences were classified. The
key result is negative: **no supported case produced a unique exact lexical span
whose surviving bracketed characters needed to be justified from CUC
`emen=restored`**. The two standalone/literal bracket cases did not exact-match
after conservative debracketing, and no restoration-aware exact case reached the
sign-evidence comparison.

The recoverable evidence instead comes from composition with the already
reviewed #78 parenthesis rule:

- 145 occurrences have bracketed material wholly inside a simple parenthesized
  group with otherwise straightforward inner syntax;
- another 28 have bracket/slash markup wholly inside that omitted group and can
  be treated as opaque because none of its characters enter the lexical core;
- across those classes the counterfactual audit finds **149 unique exact core
  spans**, **1 repeated/ambiguous core**, and **23 no-match** cases;
- 2 literal-bracket cases remain no-match;
- 108 bracket-bearing occurrences remain unsupported complex/mixed syntax.

Thus no production rule in this ticket needs to read `sign.tf`, `emen.tf`,
`cert.tf`, or `alt.tf`. The research run measured the exact pinned files for
future work:

- `sign.tf`: 316,599 bytes,
  SHA-256 `b2dc8e85175bc719a72cb5ef11bad6ca9f979d61f46434b8f1e0f50c0ab5b012`
- `emen.tf`: 563,793 bytes,
  SHA-256 `bcd7a02c652f000da1938d3e5e76c41da54665ce4ee4ca2a5fd9f0b9cb9dcec6`
- `cert.tf`: 478,896 bytes,
  SHA-256 `d4b1da7b82163bcbf2dfb82967612c41e13a2cf9491bf68a94a3c2305a2da47f`
- `alt.tf`: 146,587 bytes,
  SHA-256 `55a874dbfb34d1d1f2d730644305609c6aa42d1b3f1ca7b9c52b6dd1426bcdd3`

These are research evidence only. They are deliberately **not** added to the
production compatibility manifest because production alignment does not consume
them. Expanding the trust boundary without a rule that needs those files would
add failure modes without adding correctness.

## Production decision

The only production widening authorized by this ticket is:

> If one simple parenthesized group contains all square-bracket/slash editorial
> markup, and no square bracket or slash survives outside that group, treat the
> entire group as opaque omitted material and exact-match only the outside core.

The rule is named `parenthesis_core_opaque_group`.

It does **not** strip square brackets from surviving lexical text. It does not
claim a restored reading, and it does not inspect CUC editorial features. The
inner text is irrelevant to the lexical anchor because #78 independently
established that the parenthesized group is omitted from the exact core.

Production real-source behavior after this rule:

- exact lexical occurrences: **7,253 -> 7,402** (+149);
- ambiguous exact spans: **275 -> 276** (+1);
- `HEADWORD_NOT_FOUND`: **1,991 -> 1,841** (-150);
- square-bracket-bearing outcomes become 149 exact, 1 ambiguous, 133 not found.

The arithmetic closes exactly against the counterfactual research result.

## Remaining boundary

The 108 unsupported complex/mixed bracket expressions are not evidence for
unconditional debracketing. They require separate structural classification
before any further widening. Surviving bracketed lexical characters still have
no real-source exact case in the currently supported syntax on which to validate
a CUC `emen` agreement policy.
