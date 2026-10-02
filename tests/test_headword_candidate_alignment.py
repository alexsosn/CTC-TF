from __future__ import annotations

import unittest

from test_headword_candidate_research import _index, _record
from ugarit_context_parsing.alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentReason,
    BurnsAnchorKind,
    align_burns_source,
)
from ugarit_context_parsing.annotations import normalize_workbook_records


def _one(headword: str, words: tuple[str, ...]):
    source = normalize_workbook_records((_record(1, headword, 1),))
    index = _index({1: words})
    alignment = align_burns_source(source, index)[0]
    return source, alignment.occurrences[0]


class HeadwordCandidateAlignmentTests(unittest.TestCase):
    def test_simple_parenthesis_uses_core_only_as_exact_anchor(self):
        source, occurrence = _one("a (b)", ("a",))
        self.assertEqual(source.annotations[0].headword, "a (b)")
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.NONE)
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_LEXICAL)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
        self.assertEqual(len(occurrence.anchor_nodes), 1)

    def test_parenthesis_expanded_surface_without_contiguous_core_remains_unresolved(self):
        _, occurrence = _one("a (b) c", ("a", "b", "c"))
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.HEADWORD_NOT_FOUND)
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_STRUCTURAL)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)

    def test_repeated_parenthesis_core_is_explicit_ambiguity(self):
        _, occurrence = _one("a (b)", ("a", "x", "a"))
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(len(occurrence.candidate_spans), 2)
        self.assertTrue(all(len(span) == 1 for span in occurrence.candidate_spans))

    def test_token_internal_slash_accepts_left_or_right_exact_branch(self):
        for headword, words in (
            ("k/l m", ("k", "m")),
            ("k/l m", ("l", "m")),
        ):
            with self.subTest(words=words):
                _, occurrence = _one(headword, words)
                self.assertEqual(occurrence.reason, BurnsAlignmentReason.NONE)
                self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_LEXICAL)
                self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
                self.assertEqual(len(occurrence.anchor_nodes), 2)

    def test_two_slash_branches_on_same_line_are_not_first_hit_selected(self):
        _, occurrence = _one("q/r", ("q", "r"))
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN)
        self.assertEqual(len(occurrence.candidate_spans), 2)
        self.assertNotEqual(occurrence.candidate_spans[0], occurrence.candidate_spans[1])

    def test_unsupported_mixed_nested_and_bracketed_syntax_still_fails_closed(self):
        for headword in (
            "a (b/c)",
            "a (b (c))",
            "a [b]",
            "a / b",
        ):
            with self.subTest(headword=headword):
                _, occurrence = _one(headword, ("a", "b", "c"))
                self.assertEqual(occurrence.reason, BurnsAlignmentReason.HEADWORD_NOT_FOUND)
                self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)

    def test_plain_and_documented_trailing_markers_keep_existing_behavior(self):
        for headword in ("a", "a*", "a*†", "a!"):
            with self.subTest(headword=headword):
                _, occurrence = _one(headword, ("a",))
                self.assertEqual(occurrence.reason, BurnsAlignmentReason.NONE)
                self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)


if __name__ == "__main__":
    unittest.main()
