from __future__ import annotations

import json
import unittest

from scripts.audit_burns_alignment import (
    _research_parenthesis_candidates,
    _research_slash_candidates,
    aggregate_headword_candidate_hypothesis_stats,
)
from test_burns_tf_module import _index, _record
from ugarit_context_parsing.alignment import (
    BurnsAlignmentReason,
    align_burns_source,
)
from ugarit_context_parsing.annotations import normalize_workbook_records


class CandidateHypothesisParsingTests(unittest.TestCase):
    def test_simple_parenthesis_emits_include_and_omit_in_authored_order(self):
        self.assertEqual(
            _research_parenthesis_candidates("a (b c) d"),
            (
                ("include_group", ("a", "b", "c", "d")),
                ("omit_group", ("a", "d")),
            ),
        )
        self.assertEqual(
            _research_parenthesis_candidates("(a b) c"),
            (
                ("include_group", ("a", "b", "c")),
                ("omit_group", ("c",)),
            ),
        )

    def test_parenthesis_research_fails_closed_on_unsupported_syntax(self):
        for value in (
            "a (b) (c)",
            "a (b (c))",
            "a (b",
            "a [b] (c)",
            "a",
        ):
            with self.subTest(value=value):
                self.assertEqual(_research_parenthesis_candidates(value), ())

    def test_simple_inline_slash_emits_two_token_branches(self):
        self.assertEqual(
            _research_slash_candidates("a b/c d"),
            (
                ("slash_left", ("a", "b", "d")),
                ("slash_right", ("a", "c", "d")),
            ),
        )

    def test_slash_research_fails_closed_on_complex_or_cross_ticket_syntax(self):
        for value in (
            "a / b",
            "a b/c d/e",
            "a b/c/d",
            "a (b/c)",
            "a [b/c]",
            "a",
        ):
            with self.subTest(value=value):
                self.assertEqual(_research_slash_candidates(value), ())


class CandidateHypothesisAggregateTests(unittest.TestCase):
    def test_exact_candidate_union_distinguishes_unique_and_distinct_spans(self):
        source = normalize_workbook_records(
            (
                _record(1, headword="bʿl (mlk) x", references="I.3"),
                _record(2, headword="bʿl (mlk)", references="I.3"),
                _record(3, headword="bʿl/zzz", references="I.2"),
                _record(4, headword="zzz/bʿl", references="I.2"),
                _record(5, headword="bʿl/mlk", references="I.3"),
            )
        )
        index = _index()
        alignments = align_burns_source(source, index)
        self.assertTrue(
            all(
                occurrence.reason is BurnsAlignmentReason.HEADWORD_NOT_FOUND
                for alignment in alignments
                for occurrence in alignment.occurrences
            )
        )

        stats = aggregate_headword_candidate_hypothesis_stats(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(
            stats["parentheses"]["outcomes"],
            {
                "distinct_candidate_spans": 1,
                "unique_include_group": 1,
            },
        )
        self.assertEqual(stats["parentheses"]["eligible_occurrences"], 2)
        self.assertEqual(
            stats["parentheses"]["candidate_span_cardinality"],
            {
                "include_group": {"1": 2},
                "omit_group": {"0": 1, "1": 1},
            },
        )
        self.assertEqual(
            stats["slash"]["outcomes"],
            {
                "distinct_candidate_spans": 1,
                "unique_slash_left": 1,
                "unique_slash_right": 1,
            },
        )
        self.assertEqual(stats["slash"]["eligible_occurrences"], 3)
        self.assertEqual(
            stats["slash"]["candidate_span_cardinality"],
            {
                "slash_left": {"0": 1, "1": 2},
                "slash_right": {"0": 1, "1": 2},
            },
        )

    def test_aggregate_is_source_safe_and_counts_unsupported_shapes(self):
        source = normalize_workbook_records(
            (
                _record(1, headword="private (secret) (again)", references="I.2"),
                _record(2, headword="private / secret", references="I.2"),
            )
        )
        index = _index()
        stats = aggregate_headword_candidate_hypothesis_stats(
            source=source,
            alignments=align_burns_source(source, index),
            index=index,
        )
        payload = json.dumps(stats, sort_keys=True)

        self.assertEqual(
            stats["parentheses"]["unsupported"],
            {"multiple_or_nested": 1},
        )
        self.assertEqual(
            stats["slash"]["unsupported"],
            {"standalone_slash": 1},
        )
        for restricted in (
            "private",
            "secret",
            "again",
            "KTU 1.14",
            "I.2",
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
