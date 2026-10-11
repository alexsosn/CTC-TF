from __future__ import annotations

import unittest

from test_headword_candidate_alignment import _one
from ugarit_context_parsing.alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentReason,
    BurnsAnchorKind,
)


class BracketSafeParenthesisAlignmentTests(unittest.TestCase):
    def test_bracketed_markup_entirely_inside_omitted_group_uses_exact_core(self):
        for headword in (
            "a ([b]) d",
            "a ([b/c]) d",
            "a ([b) d",  # square-bracket imbalance is confined to omitted text
        ):
            with self.subTest(headword=headword):
                _, occurrence = _one(headword, ("a", "d"))
                self.assertEqual(occurrence.reason, BurnsAlignmentReason.NONE)
                self.assertEqual(
                    occurrence.confidence,
                    BurnsAlignmentConfidence.EXACT_LEXICAL,
                )
                self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
                self.assertEqual(len(occurrence.anchor_nodes), 2)
                self.assertEqual(
                    occurrence.match_rule,
                    "parenthesis_core_opaque_group",
                )

    def test_brackets_or_slash_surviving_in_core_are_not_stripped(self):
        for headword in (
            "[a] (b) d",
            "a (b) [d]",
            "a ([b]) d/e",
        ):
            with self.subTest(headword=headword):
                _, occurrence = _one(headword, ("a", "d"))
                self.assertEqual(
                    occurrence.reason,
                    BurnsAlignmentReason.HEADWORD_NOT_FOUND,
                )
                self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)

    def test_repeated_opaque_core_is_explicit_ambiguity(self):
        _, occurrence = _one("a ([b]) d", ("a", "d", "x", "a", "d"))
        self.assertEqual(
            occurrence.reason,
            BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN,
        )
        self.assertEqual(
            occurrence.candidate_rules,
            (
                "parenthesis_core_opaque_group",
                "parenthesis_core_opaque_group",
            ),
        )
        self.assertEqual(len(occurrence.candidate_spans), 2)


if __name__ == "__main__":
    unittest.main()
