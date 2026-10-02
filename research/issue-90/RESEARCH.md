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
