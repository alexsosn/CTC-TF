from __future__ import annotations

import json
import unittest
from dataclasses import replace

from scripts.audit_burns_alignment import aggregate_multitoken_residual_research
from test_headword_candidate_research import _index, _record
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class MultiTokenResidualResearchTests(unittest.TestCase):
    def test_structural_signatures_are_source_safe_and_hierarchy_preserving(self):
        repeated = replace(
            _record(9, "s t u", 90),
            references="I.90, 100",
        )
        marker = replace(
            _record(10, "v w*", 110),
            source_file="02 Synthetic/Worksheet 1.csv",
        )
        records = (
            _record(1, "a b c", 10),   # mask 101; b uniquely contained in bx
            _record(2, "d e f", 20),   # mask 101; e -> x unique edit1
            _record(3, "g h", 30),     # zero exact overlap
            _record(4, "i j k", 40),   # all exact, in order, non-contiguous
            _record(5, "l m", 50),     # all exact, reordered
            _record(6, "n", 60),       # single-token: excluded
            _record(7, "o p", 70),     # exact +1 neighbor: excluded
            _record(8, "q r", 80),     # exact-concat boundary window: excluded
            repeated,
            marker,
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                10: ("a", "bx", "c"),
                20: ("d", "x", "f"),
                30: ("x", "y"),
                40: ("i", "j", "x", "k"),
                50: ("m", "l"),
                60: ("x",),
                70: ("wrong",),
                71: ("o", "p"),
                80: ("qr",),
                90: ("s", "x", "u"),
                100: ("s", "x", "u"),
                110: ("v", "wx"),
            }
        )
        alignments = align_burns_source(source, index)

        stats = aggregate_multitoken_residual_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 8)
        self.assertEqual(
            stats["syntax_classes"],
            {"clean": 7, "marker_only": 1},
        )
        self.assertEqual(
            stats["classes"],
            {
                "all_tokens_in_order_noncontiguous": 1,
                "all_tokens_present_reordered": 1,
                "one_missing_unique_containment": 2,
                "one_missing_unique_edit1": 3,
                "zero_exact_token_overlap": 1,
            },
        )
        self.assertEqual(
            stats["presence_masks"],
            {"00": 1, "10": 1, "101": 4, "11": 1, "111": 1},
        )
        self.assertEqual(
            stats["unmatched_token_counts"],
            {"0": 2, "1": 5, "2": 1},
        )
        self.assertEqual(
            stats["one_missing_local_evidence"],
            {"unique_containment": 2, "unique_edit1": 3},
        )
        self.assertEqual(stats["distinct_annotations"], 7)
        self.assertEqual(
            stats["annotation_occurrence_multiplicity"],
            {"1": 6, "2": 1},
        )
        self.assertEqual(
            stats["workbook_classes"]["2"],
            {"one_missing_unique_containment": 1},
        )

    def test_multiple_local_candidates_remain_ambiguous_diagnostic(self):
        source = normalize_workbook_records((_record(1, "a b c", 10),))
        index = _index({10: ("a", "bx", "by", "c")})
        alignments = align_burns_source(source, index)

        stats = aggregate_multitoken_residual_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 1)
        self.assertEqual(
            stats["classes"],
            {"one_missing_ambiguous_local": 1},
        )
        self.assertEqual(
            stats["one_missing_local_evidence"],
            {"ambiguous_containment": 1},
        )

    def test_repeated_exact_tokens_do_not_reuse_the_same_cuc_word(self):
        source = normalize_workbook_records((_record(1, "a a c", 10),))
        index = _index({10: ("a", "bx", "c")})
        alignments = align_burns_source(source, index)
        stats = aggregate_multitoken_residual_research(
            source=source, alignments=alignments, index=index
        )
        self.assertEqual(stats["occurrences"], 1)
        self.assertEqual(stats["presence_masks"], {"101": 1})
        self.assertEqual(stats["unmatched_token_counts"], {"1": 1})
        self.assertEqual(stats["classes"], {"partial_exact_token_overlap": 1})

    def test_exact_cuc_words_are_not_counted_as_edit_candidates_for_missing_tokens(self):
        source = normalize_workbook_records((_record(1, "d e f", 10),))
        index = _index({10: ("d", "x", "f")})
        alignments = align_burns_source(source, index)
        stats = aggregate_multitoken_residual_research(
            source=source, alignments=alignments, index=index
        )
        self.assertEqual(stats["classes"], {"one_missing_unique_edit1": 1})
        self.assertEqual(stats["one_missing_local_evidence"], {"unique_edit1": 1})

    def test_partial_exact_hits_record_order_independently_of_near_match(self):
        source = normalize_workbook_records((
            _record(1, "a b c", 10),
            _record(2, "d e f", 20),
            _record(3, "g h", 30),
        ))
        index = _index({
            10: ("c", "bx", "a"),  # mask 101 but exact a/c are reversed
            20: ("d", "x", "f"),   # mask 101 and exact d/f are in order
            30: ("x", "y"),        # mask 00, no exact-order evidence
        })
        alignments = align_burns_source(source, index)
        stats = aggregate_multitoken_residual_research(
            source=source, alignments=alignments, index=index
        )
        self.assertEqual(stats["occurrences"], 3)
        self.assertEqual(stats["presence_masks"], {"00": 1, "101": 2})
        self.assertEqual(
            stats["exact_hit_order"],
            {"in_order": 1, "no_exact_hits": 1, "out_of_order": 1},
        )
        self.assertEqual(
            stats["classes"],
            {"one_missing_unique_containment": 1,
             "one_missing_unique_edit1": 1,
             "zero_exact_token_overlap": 1},
        )

    def test_one_containing_word_with_multiple_embeddings_is_ambiguous(self):
        source = normalize_workbook_records((_record(1, "a aba c", 10),))
        index = _index({10: ("a", "ababa", "c")})
        alignments = align_burns_source(source, index)
        stats = aggregate_multitoken_residual_research(
            source=source, alignments=alignments, index=index
        )
        self.assertEqual(stats["occurrences"], 1)
        self.assertEqual(stats["presence_masks"], {"101": 1})
        self.assertEqual(stats["classes"], {"one_missing_ambiguous_local": 1})
        self.assertEqual(stats["one_missing_local_evidence"], {"ambiguous_containment": 1})

    def test_payload_does_not_expose_source_strings_ids_locators_or_nodes(self):
        source = normalize_workbook_records((_record(1, "secret private", 10),))
        index = _index({10: ("secret", "privatex")})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_multitoken_residual_research(
                source=source,
                alignments=alignments,
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret",
            "private",
            "privatex",
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
