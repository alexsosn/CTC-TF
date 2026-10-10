# #85 Plan: source-safe run-level independence diagnostics

1. **Research** the current exact neighbor probe, run grouping, annotation and occurrence IDs, and previous #80 results. Only neighbor-unique evidence enters runs. Preserve current accepted exact-matcher logic.

2. **RED tests** using a synthetic reviewed-index fixture:
   - a run with distinct annotations on successive cited lines reports run length 2 and annotation-support bucket 2;
   - two different annotations on one cited line count as a single run position but two independent annotations;
   - duplicated references to an identical cited line do not lengthen a run or increase distinct annotations;
   - runs do not join across gaps, tablets, columns or opposite offsets;
   - ambiguous neighbor hits never count toward run evidence;
   - report is source-safe and fails on invalid annotation IDs.

3. **GREEN** modify only `aggregate_line_address_drift_stats()` to build annotation sets in memory; publish total distinct-annotation and position counters, independent-annotation-by-run-length histograms and long-run (>2 positions) source-safe aggregates. No production reference mapping.

4. **Real pinned gate** tie run accounting to the existing line-drift aggregate: sum run-length × run-count equals distinct unique-rescue positions by offset, and sum of unique-offset occurrence counts remains total unique-neighbor outcomes. Record current real-source histograms, comparison against #80 and annotation counts.

5. **Review** independent exact-head adversarial pass of code/CI and real statistics. Explicitly challenge whether run grouping is conflated with lexical coincidence, whether duplicate rows and unique-position counts are handled, whether identifiers leak, or whether diagnostic counts are misrepresented as line-remapping evidence.
