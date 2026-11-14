# #115 private source-case review — research (2026-11-15)

## Baseline

The merged source-safe `aggregate_multitoken_residual_research` classifies 380 eligible multi-token clean/marker-only `HEADWORD_NOT_FOUND` occurrences from 45 pinned Burns Workbooks and reviewed CUC 0.2.8; **23** occurrences have one uniquely containing local CUC word and **39** have one unique edit-distance-1 word after exact Burns words are consumed. This **62 occurrence** count must not be mistaken for 62 independent annotations or valid lexical alignments. The existing independent-annotation union and exact-hit order cross-tab (#115) help choose cases, but contain deliberately no source forms, CUC word context or locators. The opt-in `--private-out-of-order` (#114) is restricted to order-conflicting cases, not all one-missing candidates.

The production matcher remains exact/source-evidenced; proximity is **not** morphological or editorial evidence. A researcher needs the original headword and reference, token/missing-token relation, actual ordered CUC `g_cons` words and candidate word in a restricted local file to compare with licensed PDF, grammar and editorial evidence. The real licensed source is accessed only in CI and user-local environments; public outputs must remain aggregate-only.

## Decision

Add an explicit `--private-one-missing PATH` research output to the existing audit CLI, with owner-only atomic JSON and the same three protected input roots as the existing private reports. Select cases using the *same* eligibility and exclusion gates as the public aggregate (clean/marker; >=2 tokens; HEADWORD_NOT_FOUND; indexed line; no neighboring exact recovery; no token-boundary exact window); consume exact CUC words with multiplicity before inspecting one absent token. Include only unique containment or unique edit1, with the exact candidate from the unconsumed CUC words, ordered line words, Burns source/reference/worksheet provenance, class, presence mask and exact-hit order. Preserve separate occurrences and deduplicated annotation counts; reconcile per-class occurrences and independent annotation union with the existing safe aggregate. Distinguish order conflict from in-order evidence. Never promote near-matches to production TF features/nodes.

## Adversarial threats

- Duplicate words, multiple embeddings and ambiguous edit1 ties must not be called unique.
- Exact tokens consumed for other Burns positions must not be eligible as candidate words; exact-hit order must remain independent of near-match class.
- Repeated citations and one annotation appearing in both classes must not inflate unique evidence.
- Neighbors and exact concatenated word-boundary windows have higher-priority explanations and must be excluded.
- No local case data or precise path can reach stdout, committed data, CI logs, artifacts or downloaded reports.
- All three private destinations must be distinct after symlink resolution, outside checkout, source and reviewed CUC roots; reject unsafe paths before optional Workbooks acquisition.
- Real-data verification must assert only counts/permissions and a PASS marker, never leak case payload.
