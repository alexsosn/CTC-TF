from __future__ import annotations

import json
import unittest
from dataclasses import replace

from test_headword_candidate_research import _index, _record
from scripts.audit_burns_alignment import aggregate_residual_clean_gap_research
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class ResidualCleanGapResearchTests(unittest.TestCase):
    def test_classification_hierarchy_is_mutually_exclusive_and_source_safe(self):
        records = (
            _record(1, "neighbor", 1),
            _record(2, "ab cd", 10),
            _record(3, "a c", 20),
            _record(4, "a b", 30),
            _record(5, "ab", 40),
            _record(6, "abc", 50),
            _record(7, "a b", 60),
            _record(8, "foo bar", 70),
            replace(
                _record(9, "marker*", 80),
                source_file="02 Synthetic/Worksheet 1.csv",
            ),
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                1: ("wrong",),
                2: ("neighbor",),
                10: ("abcd",),
                20: ("a", "x", "c"),
                30: ("b", "a"),
                40: ("zabx",),
                50: ("abd",),
                60: ("a", "x"),
                70: ("x", "y"),
                80: ("z",),
            }
        )
        alignments = align_burns_source(source, index)
        self.assertEqual(
            sum(
                occurrence.reason.value == "headword_not_found"
                for alignment in alignments
                for occurrence in alignment.occurrences
            ),
            9,
        )

        stats = aggregate_residual_clean_gap_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 9)
        self.assertEqual(
            stats["syntax_classes"],
            {"clean": 8, "marker_only": 1},
        )
        self.assertEqual(
            stats["classes"],
            {
                "all_tokens_in_order_noncontiguous": 1,
                "all_tokens_present_reordered": 1,
                "neighbor_evidence": 1,
                "no_exact_token_overlap": 2,
                "partial_exact_token_overlap": 1,
                "token_boundary_exact": 1,
                "unique_single_token_containment": 1,
                "unique_single_token_edit1": 1,
            },
        )
        self.assertEqual(sum(stats["classes"].values()), stats["occurrences"])
        self.assertEqual(stats["neighbor_evidence"], {"unique_neighbor": 1})
        self.assertEqual(
            stats["token_boundary_span_cardinality"],
            {"0": 8, "1": 1},
        )
        self.assertEqual(
            stats["single_token_unique_edit1_operations"],
            {"substitution": 1},
        )
        self.assertEqual(
            stats["workbook_classes"]["2"],
            {"no_exact_token_overlap": 1},
        )

    def test_expression_syntax_failures_are_excluded(self):
        records = (
            _record(1, "a (b)", 1),
            _record(2, "[a]/b", 2),
            _record(3, "clean-miss", 3),
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                1: ("wrong",),
                2: ("wrong",),
                3: ("other",),
            }
        )
        alignments = align_burns_source(source, index)
        stats = aggregate_residual_clean_gap_research(
            source=source,
            alignments=alignments,
            index=index,
        )
        self.assertEqual(stats["occurrences"], 1)
        self.assertEqual(stats["syntax_classes"], {"clean": 1})

    def test_payload_does_not_expose_source_strings_ids_locators_or_nodes(self):
        source = normalize_workbook_records((_record(1, "secret-token", 10),))
        index = _index({10: ("private-token",)})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_residual_clean_gap_research(
                source=source,
                alignments=alignments,
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret-token",
            "private-token",
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
