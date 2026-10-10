# #85 Research: independent support for exact neighbor-line run hypotheses

## Background and falsifiable question

Burns↔CUC line-offset diagnostics already count exact neighbor-only lexical hits and group **distinct cited line numbers** into contiguous runs for each (tablet, column, signed offset). The old #80 candidate-neighbor audit recorded a -1 run of 7, a +1 run of 6, a +1 run of 4, and other shorter runs, but those figures predate the current expression parser and cannot be taken as evidence of a structural reference-number offset.

The current run histogram counts line positions, not how many independent Burns annotations support those positions. Multiple annotation references to the same cited line, repeated records and two annotations sharing a candidate location must not be conflated with a longer structural run.

## Scope and safety

Extend the *diagnostic* run characterization without modifying reference resolution or match behavior:
- for every exact, **unique span at exactly one neighboring offset**, retain in memory the IDs of independent Burns annotations by (tablet, column, offset, cited line);
- separately count distinct unique-rescue annotations, distinct (tablet, column, signed-offset, cited-line) positions, and occurrence multiplicity;
- for each run of adjacent *unique positions*, report aggregate cardinality of contributing distinct Burns annotations, by offset and run length (histograms, not loci);
- classify long runs length >= 3 by number of independent annotations and compare with any single-annotation-only runs;
- omit all Burns forms, CUC forms, tablet/column/line identifiers, source rows, annotation IDs, source pages and node IDs from committed/CI data.

**Do not** infer an offset correction from either lexical hits or independent cardinality. Verification of local run loci against Burns source pages, CUC edition segmentation, line breaks and editorial context remains private/manual and is required before a deterministic remapping proposal.

## Independent evidence boundary

A candidate rescues only if the *entire production headword candidate sequence* has **one exact CUC span on exactly one neighboring line** within the same tablet and column, never across structures. Multiple offsets and repeated hits on the same neighbor remain ambiguous and are excluded.

## Follow-ups

After real Workbooks CI, compare current long-run distribution with historic #80; investigate changed parser semantics and independent annotation support. Any proposal to modify line references requires a separate ticket with preserved RED, structural criteria independent of lexical content, negative controls at tablet/column boundaries, and a private edition-based explanation.
