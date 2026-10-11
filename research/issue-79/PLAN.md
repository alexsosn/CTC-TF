# #79 Plan: research -> TDD -> restoration-aware production rule

## Gate 1 - research RED

Add tests for:

- balanced partial-token, full-token, and multi-token bracket masks;
- nested/unbalanced/empty bracket syntax fails closed;
- trailing editorial markers do not become lexical/restoration characters;
- source-safe classification of brackets surviving vs disappearing under
  `parenthesis_core`;
- exact sign-position agreement / missing / extra restoration evidence;
- sign-sequence mismatch fails closed;
- aggregate payload contains no source strings or ids.

Do not alter `headword_candidates()` yet.

## Gate 2 - reviewed-CUC real audit

In the pinned real-source workflow, load `sign emen cert alt` from the exact
reviewed CUC checkout for **research only** and measure:

- sign/g_cons mapping success for candidate words;
- bracket syntax/composition distribution;
- debracketed exact-span cardinality;
- restoration agreement/disagreement classes;
- `cert`/`alt` co-occurrence;
- how many brackets disappear entirely with `parenthesis_core`.

If evidence does not support a safe production rule, stop and document the
boundary.

## Gate 3 - trust contract

Before production alignment reads editorial CUC features:

- add exact reviewed fingerprints for every additional CUC TF file used;
- extend the compatibility manifest and tests;
- load the editorial features through the reviewed index, not an unverified
  side channel.

## Gate 4 - production RED

For each research-authorized class:

- exact full-word restoration;
- exact partial-word restoration;
- exact multiword restoration;
- parenthesis-core composition where surviving bracket masks are supported;
- bracket only inside omitted parenthesized material;
- missing/extra restoration evidence -> unresolved;
- conflicting `cert`/`alt` according to the researched policy;
- repeated lexical span -> ambiguity;
- unsupported mixed slash/bracket syntax -> fail closed;
- ordinary #78/plain behavior unchanged.

## Gate 5 - GREEN + real module

Implement only the evidenced rules. Add a distinct `match_rule` value so a
restoration-aware exact span is never indistinguishable from literal matching.

Re-run the full Workbooks module, exact CUC warp invariants, Context-Fabric /
cfabric-mcp consumer smoke and all existing audits. Report the exact lexical
coverage delta and disagreement counts.

## Gate 6 - logically independent exact-head review

Review against the real data and upstream CUC feature semantics. Attack
unconditional bracket stripping, positional drift between `g_cons` and sign
slots, unverified editorial files, cert/alt suppression, ambiguity collapse,
and feature-only module regressions.
