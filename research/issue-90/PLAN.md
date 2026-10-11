# #90 Plan

## Gate 1 - RED research contract

Add tests for a pure source-safe unsupported-expression classifier and aggregate
counterfactual audit.

Required cases:

- unbalanced brackets;
- multiple/nested parentheses;
- simple parenthesis with markup surviving outside the omitted group;
- bracket+slash without parentheses;
- multiple slash/bracket groups;
- marker flag retained only as aggregate metadata;
- conservative debracketing exact-span cardinality;
- debracketed production-candidate span union cardinality;
- aggregate output contains no source strings, ids, locators or node ids.

No production matcher change in this gate.

## Gate 2 - GREEN research audit

Implement audit helpers in `scripts/audit_burns_alignment.py` and add the
aggregate payload to the pinned real Workbooks workflow.

The denominator must independently close to the 108 unsupported bracket-bearing
resolved-line occurrences established by #79.

## Gate 3 - interpretation

Record the real structural distribution and exact-span counterfactuals in
`research/issue-90/RESEARCH.md`.

If one class satisfies the production decision rule, continue with a second
preserved RED/GREEN production sub-loop. If not, do not invent normalization.

## Gate 4 - production sub-loop, only if authorized

For any evidenced rule:

- preserve restoration positions;
- extend the reviewed CUC fingerprint only if production consumes
  `sign/emen/cert/alt`;
- exact match only;
- preserve ambiguity;
- publish a distinct `burns_match_rule_N`;
- keep unsupported cases unresolved.

## Gate 5 - real data and independent review

Run exact-head unit, real Workbooks, reviewed-CUC/cfabric and release-surface
gates. Review from the editorial-semantics boundary and attack unconditional
debracketing, mask drift, candidate overgeneralization and source-data leakage.
