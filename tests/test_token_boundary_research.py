from __future__ import annotations

import json
import unittest

from test_headword_candidate_research import _index, _record
from scripts.audit_burns_alignment import aggregate_token_boundary_research
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class TokenBoundaryResearchTests(unittest.TestCase):
    def test_boundary_patterns_are_aggregate_and_directional(self):
        records = (
            _record(1, "ab cd", 1),   # Burns 2 -> CUC 1: merge
            _record(2, "abcd", 2),    # Burns 1 -> CUC 2: split
            _record(3, "ab cd", 3),   # Burns 2 -> CUC 2: resegment
            _record(4, "ab", 4),      # two split windows: ambiguity
            _record(5, "foo", 5),     # ordinary residual, no boundary match
            _record(6, "a (b)", 6),   # expression syntax: excluded
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                1: ("abcd",),
                2: ("ab", "cd"),
                3: ("a", "bcd"),
                4: ("a", "b", "x", "a", "b"),
                5: ("bar",),
                6: ("wrong",),
            }
        )
        alignments = align_burns_source(source, index)

        stats = aggregate_token_boundary_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 4)
        self.assertEqual(
            stats["span_cardinality"],
            {"1": 3, "2+": 1},
        )
        self.assertEqual(
            stats["directions"],
            {"merge": 1, "resegment": 1, "split": 2},
        )
        self.assertEqual(
            stats["token_count_transitions"],
            {"1->2": 2, "2->1": 1, "2->2": 1},
        )
        self.assertEqual(
            stats["window_directions"],
            {"merge": 1, "resegment": 1, "split": 3},
        )
        self.assertEqual(stats["excluded_expression_syntax"], 1)
        self.assertEqual(stats["eligible_clean_marker_gaps"], 5)

    def test_payload_contains_no_lexical_strings_ids_locators_or_nodes(self):
        source = normalize_workbook_records((_record(1, "secret token", 10),))
        index = _index({10: ("secrettoken",)})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_token_boundary_research(
                source=source,
                alignments=alignments,
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret",
            "token",
            "secrettoken",
            "KTU 1.14",
            "I.10",
            source.records[0].record_id,
            source.annotations[0].annotation_id,
            "500",
            "100",
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
