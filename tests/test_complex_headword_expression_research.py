from __future__ import annotations

import json
import unittest

from test_headword_candidate_research import _index, _record
from scripts.audit_burns_alignment import (
    aggregate_complex_headword_expression_research,
    classify_unsupported_bracket_expression,
)
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class UnsupportedBracketClassifierTests(unittest.TestCase):
    def test_classifies_structural_failure_before_any_lexical_guess(self):
        cases = {
            "a [b": "unbalanced_square_brackets",
            "a ([b]": "unbalanced_parentheses",
            "a ([b]) (c)": "multiple_or_nested_parentheses",
            "a ([b]) c/d": "simple_parenthesis_mixed_markup",
            "[a]/b": "bracket_slash_no_parenthesis",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                result = classify_unsupported_bracket_expression(value)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result["class"], expected)

    def test_shapes_already_owned_by_issue_79_are_not_reclassified(self):
        for value in (
            "[a]bc",
            "a ([b]) c",
            "a ([b/c]) c",
        ):
            with self.subTest(value=value):
                self.assertIsNone(classify_unsupported_bracket_expression(value))

    def test_orthogonal_flags_are_source_safe_structure_only(self):
        result = classify_unsupported_bracket_expression("a ([b][c]) d/e/f*")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["class"], "simple_parenthesis_mixed_markup")
        self.assertTrue(result["slash"])
        self.assertTrue(result["multiple_slashes"])
        self.assertTrue(result["multiple_bracket_groups"])
        self.assertTrue(result["trailing_editorial_marker"])
        self.assertTrue(result["debracketable"])


class ComplexHeadwordExpressionAggregateTests(unittest.TestCase):
    def test_counterfactual_debracketing_is_measured_without_changing_alignment(self):
        records = (
            _record(1, "a [b", 1),
            _record(2, "c ([d]) (e)", 2),
            _record(3, "f ([g]) h/i", 3),
            _record(4, "[j]/k", 4),
            _record(5, "l ([m]", 5),
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                1: ("a", "b"),
                2: ("c",),
                3: ("f", "h"),
                4: ("j",),
                5: ("l",),
            }
        )
        alignments = align_burns_source(source, index)

        # These are deliberately outside the current production grammar.
        self.assertTrue(
            all(
                occurrence.reason.value == "headword_not_found"
                for alignment in alignments
                for occurrence in alignment.occurrences
            )
        )

        stats = aggregate_complex_headword_expression_research(
            source=source,
            alignments=alignments,
            index=index,
        )
        self.assertEqual(stats["occurrences"], 5)
        self.assertEqual(
            stats["shape_classes"],
            {
                "bracket_slash_no_parenthesis": 1,
                "multiple_or_nested_parentheses": 1,
                "simple_parenthesis_mixed_markup": 1,
                "unbalanced_parentheses": 1,
                "unbalanced_square_brackets": 1,
            },
        )
        self.assertEqual(
            stats["flags"],
            {
                "debracketable": 4,
                "slash": 2,
            },
        )
        self.assertEqual(
            stats["debracketed_literal_span_cardinality"],
            {"0": 4},
        )
        self.assertEqual(
            stats["debracketed_candidate_span_cardinality"],
            {"0": 3, "1": 1},
        )
        self.assertEqual(
            stats["debracketed_matching_rules"],
            {"slash_left": 1},
        )

    def test_payload_contains_no_source_strings_ids_or_nodes(self):
        source = normalize_workbook_records((_record(1, "[secret]/private", 1),))
        index = _index({1: ("secret",)})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_complex_headword_expression_research(
                source=source,
                alignments=alignments,
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret",
            "private",
            "KTU 1.14",
            "I.1",
            source.records[0].record_id,
            source.annotations[0].annotation_id,
            "100",
            "500",
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
