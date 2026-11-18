# Product goals — CTC-TF / ugarit-context-parsing

## Users and purpose

Researchers of Ugaritic religion, cultic vocabulary and textual contexts should be able to overlay Duncan Coe Burns's licensed Workbook annotations on the exact compatible Copenhagen Ugaritic Corpus (CUC) without altering CUC node identity or redistributing restricted data.

## Representative research journeys

1. Locally extract authorized Burns Workbooks and construct a feature-only module over a reviewed CUC checkout.
2. Retrieve *all* exact Burns lexical occurrences, including multiple independently annotated occurrences on one word and multiword spans across every numbered feature lane.
3. Filter occurrences by source category and semantic status, inspect the originating worksheet and source context, and distinguish an original Burns headword from a verified lemma.
4. Inspect ambiguous, unmatched or excluded alignments without having them silently promoted into lexical facts.
5. Load and query the result through standard Text-Fabric with reproducible parent/source identities.

## Minimum usable release

A researcher following only public software instructions can obtain their own permitted inputs, build and load the module, run a documented all-lanes query, and reproduce a source-consistent occurrence count. A clean install, genuine source/parent compatibility check and independently reviewed query results are required. The published software must not embed restricted Workbook content or generated Burns datasets.

## Boundaries and priorities

CUC owns the warp, slots and textual source. This repo owns extraction, alignment, query helpers and Burns-only features. Do not create independent synthetic lexical nodes, a competing CUC corpus or a universal annotation framework. Next complete the researcher-ready release path for the all-lanes query API (issues #146/#149), using minimal support for normal squash merges rather than a new provenance protocol.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
