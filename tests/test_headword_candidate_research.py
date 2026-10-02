from __future__ import annotations

import json
import unittest
from types import MappingProxyType

from scripts.audit_burns_alignment import (
    aggregate_headword_candidate_research,
    simple_parenthesis_candidate_tokens,
    simple_token_slash_candidate_tokens,
)
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cuc_index import ReviewedCucIndex
from ugarit_context_parsing.source import WorkbookRecord


def _record(row: int, headword: str, line: int) -> WorkbookRecord:
    return WorkbookRecord(
        source_file="01 Synthetic/Worksheet 1.csv",
        source_row=row,
        source_page=row,
        section="Section alpha",
        root="",
        headword=headword,
        ktu="1.14",
        references=f"I.{line}",
        locus="",
        room="",
        point="",
        depth="",
        disputed="",
        comments="private-comment",
    )


def _index(lines: dict[int, tuple[str, ...]]) -> ReviewedCucIndex:
    line_nodes: dict[tuple[str, str, int], int] = {}
    bare: dict[tuple[str, int], tuple[int, ...]] = {}
    line_words: dict[int, tuple[int, ...]] = {}
    word_g_cons: dict[int, str] = {}
    word_slots: dict[int, tuple[int, ...]] = {}
    next_word = 100
    next_slot = 1
    next_line = 500
    for line, values in sorted(lines.items()):
        words: list[int] = []
        for value in values:
            word = next_word
            next_word += 1
            word_g_cons[word] = value
            word_slots[word] = (next_slot,)
            next_slot += 1
            words.append(word)
        line_node = next_line
        next_line += 1
        line_nodes[("KTU 1.14", "I", line)] = line_node
        bare[("KTU 1.14", line)] = (line_node,)
        line_words[line_node] = tuple(words)
    return ReviewedCucIndex(
        compatibility=None,
        tablet_nodes=MappingProxyType({"KTU 1.14": 900}),
        column_nodes=MappingProxyType({("KTU 1.14", "I"): 800}),
        line_nodes=MappingProxyType(line_nodes),
        bare_line_candidates=MappingProxyType(bare),
        line_words=MappingProxyType(line_words),
        word_g_cons=MappingProxyType(word_g_cons),
        word_slots=MappingProxyType(word_slots),
    )


class CandidateParserResearchTests(unittest.TestCase):
    def test_simple_parenthesis_candidates_preserve_existing_token_normalization(self):
        self.assertEqual(
            simple_parenthesis_candidate_tokens("a (b c*) d†"),
            (("a", "d"), ("a", "b", "c", "d")),
        )

    def test_simple_parenthesis_parser_fails_closed_on_unsupported_shapes(self):
        for value in (
            "a (b) (c)",
            "a (b (c))",
            "a (b",
            "a [b] (c)",
            "a (b/c)",
            "(a)",
        ):
            with self.subTest(value=value):
                self.assertIsNone(simple_parenthesis_candidate_tokens(value))

    def test_simple_token_internal_slash_preserves_surrounding_tokens(self):
        self.assertEqual(
            simple_token_slash_candidate_tokens("a b/c* d†"),
            (("a", "b", "d"), ("a", "c", "d")),
        )

    def test_slash_parser_fails_closed_on_standalone_multiple_or_mixed_shapes(self):
        for value in (
            "a / b",
            "a/b c/d",
            "a//b",
            "/a",
            "a/",
            "a (b/c)",
            "a [b/c]",
        ):
            with self.subTest(value=value):
                self.assertIsNone(simple_token_slash_candidate_tokens(value))


class CandidateResearchAggregateTests(unittest.TestCase):
    def test_realistic_exact_line_outcomes_are_classified_without_changing_alignment(self):
        records = (
            _record(1, "a (b)", 1),      # core only
            _record(2, "c (d)", 2),      # core + expanded nested
            _record(3, "e (f) g", 3),    # expanded only (core e g is non-contiguous)
            _record(4, "h (i) j", 4),    # core only
            _record(5, "k/l m", 5),      # left only
            _record(6, "n/o p", 6),      # right only
            _record(7, "q/r", 7),        # both branches on same line, distinct spans
            _record(8, "s/t", 8),        # left branch repeated -> ambiguity
            _record(9, "u (v/w)", 9),    # excluded mixed syntax
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                1: ("a",),
                2: ("c", "d"),
                3: ("e", "f", "g"),
                4: ("h", "j"),
                5: ("k", "m"),
                6: ("o", "p"),
                7: ("q", "r"),
                8: ("s", "x", "s"),
                9: ("u",),
            }
        )
        alignments = align_burns_source(source, index)

        # Research accounting is counterfactual and must remain stable even
        # after production learns an evidenced syntax class.
        self.assertTrue(
            any(
                occurrence.reason.value == "none"
                for alignment in alignments
                for occurrence in alignment.occurrences
            )
        )

        stats = aggregate_headword_candidate_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(
            stats["parentheses"],
            {
                "eligible_occurrences": 4,
                "outcomes": {
                    "core_and_expanded": 1,
                    "core_only": 2,
                    "expanded_only": 1,
                    "no_match": 0,
                    "ambiguous": 0,
                },
                "core_span_cardinality": {"0": 1, "1": 3},
                "expanded_span_cardinality": {"0": 2, "1": 2},
            },
        )
        self.assertEqual(
            stats["token_internal_slash"],
            {
                "eligible_occurrences": 4,
                "outcomes": {
                    "both_branches": 1,
                    "left_only": 1,
                    "right_only": 1,
                    "no_match": 0,
                    "ambiguous": 1,
                },
                "left_span_cardinality": {"0": 1, "1": 2, "2+": 1},
                "right_span_cardinality": {"0": 2, "1": 2},
            },
        )
        self.assertEqual(stats["excluded_mixed_or_unsupported"], 1)

    def test_aggregate_payload_contains_no_source_strings_or_ids(self):
        source = normalize_workbook_records((_record(1, "secret (private)", 1),))
        index = _index({1: ("secret",)})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_headword_candidate_research(
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
            "private-comment",
            source.annotations[0].annotation_id,
            source.records[0].record_id,
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
