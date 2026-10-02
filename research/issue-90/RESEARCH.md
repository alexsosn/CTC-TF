# #90 Research: remaining complex bracket/mixed headword expressions

## Boundary inherited from #79

The pinned real-source #79 audit covers 283 square-bracket-bearing resolved-line
occurrences. The safe production rule recovers only expressions where all
bracket/slash markup lies inside one already-evidenced omitted parenthesized
group. After that rule:

- 149 bracket-bearing occurrences are exact lexical anchors;
- 1 is an exact-span ambiguity;
- 25 supported-shape cases still have no exact core;
- **108 occurrences remain structurally unsupported**.

Those 108 must be understood before #81; they are expression-grammar failures,
not clean-headword morphology evidence.

## Research goals

1. Partition the 108 unsupported occurrences by source-safe structural shape.
2. Measure whether conservative **counterfactual** debracketing exposes exact CUC
   spans, without treating that as permission to strip brackets in production.
3. Identify whether any recurrent class has a finite deterministic candidate
   semantics worth a separate production RED.
4. Keep restoration-bearing lexical text fail-closed unless exact CUC editorial
   evidence can be mapped under the #79 trust boundary.

## Structural classifier

For bracket-bearing expressions that #79 classifies as unsupported, distinguish
at least:

- unbalanced square brackets;
- unbalanced parentheses;
- multiple or nested parenthesized groups;
- one simple parenthesized group with bracket/slash markup surviving outside the
  omitted group;
- bracket + slash with no parenthesis;
- balanced literal bracket syntax not accepted by the prior composition path;
- other recurrent structure, if observed.

Also aggregate orthogonal flags:

- slash present;
- multiple slash characters;
- multiple square-bracket groups;
- trailing `*†!?` marker;
- bracket syntax balanced enough for conservative debracketing.

No source strings, locators, ids or node ids may appear in committed/CI output.

## Counterfactual lexical probes

For unsupported expressions where `parse_square_bracket_mask()` succeeds:

1. preserve the authored restoration mask;
2. remove only square-bracket delimiters to obtain the debracketed expression;
3. measure exact contiguous CUC spans for the debracketed **literal** token
   sequence;
4. separately pass the debracketed expression through the already-reviewed
   production `headword_candidates()` grammar and union its exact spans.

These are research probes only. A unique debracketed match is not sufficient for
production because surviving restored characters still require sign-level CUC
editorial agreement.

## Decision rule

A new production rule is considered only if a narrow structural class has:

- deterministic parsing;
- recurrent exact cited-line support;
- unambiguous propagation of bracket/restoration positions through the selected
  lexical candidate;
- a defined CUC `emen/cert/alt` policy where restored characters survive;
- explicit ambiguity behavior.

Otherwise #90 closes the class as a documented fail-closed boundary and passes
only truly clean/marker-only misses to #81.


## Real-source result

Pinned Workbooks + reviewed CUC 0.2.8 on research GREEN head
`322c803e811cf4e558bb6d881ad33d97449e3e51` passed the real-source gate and
the denominator closes exactly against #79:

- #79 unsupported bracket-bearing resolved-line occurrences: **108**;
- #90 classified occurrences: **108**.

Structural classes:

- multiple or nested parenthesized groups: **72**;
- unbalanced square brackets: **32**;
- one simple parenthesized group with surviving mixed markup: **4**.

No other unsupported shape occurs in the pinned source population.

Orthogonal properties:

- conservatively debracketable: **76**;
- slash present: **28**;
- multiple slash characters: **28**;
- multiple square-bracket groups: **4**;
- trailing `*†!?` marker: **29**.

### Counterfactual exact matching

All 76 conservatively debracketable unsupported expressions were tested against
their cited CUC line without changing production alignment.

Debracketed literal token sequence:

- zero exact spans: **76**;
- one exact span: **0**;
- repeated exact spans: **0**.

Debracketed expression passed through the already-reviewed production candidate
grammar:

- zero exact spans: **76**;
- one exact span: **0**;
- repeated exact spans: **0**;
- matching candidate rules: **none**.

The remaining 32 expressions have unbalanced square brackets and therefore do
not admit even conservative debracketing.

## Decision

No production widening is justified by #90.

The 108 cases are not hiding a straightforward bracket-removal or composition
rule:

1. 32 are malformed/unbalanced at the square-bracket syntax level;
2. 72 contain multiple/nested parenthesized grouping that has no reviewed
   semantics yet;
3. 4 retain mixed markup outside the one simple parenthesized form;
4. every one of the 76 structurally debracketable cases still has no exact cited
   CUC span under either literal or already-authorized candidate semantics.

Therefore #90 terminates at the research boundary. No CUC editorial feature is
added to the production trust contract, no `burns_match_rule_N` value is added,
and no unsupported occurrence is promoted to a lexical feature.

These 108 cases remain explicit expression-syntax failures and must stay out of
#81's clean/marker-only morphology/tokenization denominator.
