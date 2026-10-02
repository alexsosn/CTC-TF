from __future__ import annotations

import json
import unittest
from types import MappingProxyType

from scripts.audit_burns_alignment import (
    compare_cuc_restoration_mask,
    opaque_parenthesis_core_with_inner_brackets,
    parenthesis_core_with_bracket_mask,
)
from ugarit_context_parsing.cuc_index import ReviewedCucIndex
from ugarit_context_parsing.headword_expression import parse_square_bracket_mask


def _index() -> ReviewedCucIndex:
    return ReviewedCucIndex(
        compatibility=None,
        tablet_nodes=MappingProxyType({"KTU 1.1": 900}),
        column_nodes=MappingProxyType({("KTU 1.1", "I"): 800}),
        line_nodes=MappingProxyType({("KTU 1.1", "I", 1): 700}),
        bare_line_candidates=MappingProxyType({("KTU 1.1", 1): (700,)}),
        line_words=MappingProxyType({700: (100, 101)}),
        word_g_cons=MappingProxyType({100: "abc", 101: "de"}),
        word_slots=MappingProxyType({100: (1, 2, 3), 101: (4, 5)}),
    )


class SquareBracketMaskParserTests(unittest.TestCase):
    def test_partial_full_and_multitoken_masks(self):
        parsed = parse_square_bracket_mask("a[b]c* [d e]†")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.tokens, ("abc", "d", "e"))
        self.assertEqual(parsed.restored_positions, ((1,), (0,), (0,)))
        self.assertEqual(parsed.debracketed, "abc* d e†")

    def test_markers_are_not_restoration_characters(self):
        parsed = parse_square_bracket_mask("[ab]*†")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.tokens, ("ab",))
        self.assertEqual(parsed.restored_positions, ((0, 1),))

    def test_nested_unbalanced_empty_and_unbracketed_fail_closed(self):
        for value in ("a[[b]]", "a[b", "a]b", "a[]b", "abc"):
            with self.subTest(value=value):
                self.assertIsNone(parse_square_bracket_mask(value))


class ParenthesisBracketCompositionTests(unittest.TestCase):
    def test_brackets_inside_omitted_group_disappear_from_core(self):
        candidate = parenthesis_core_with_bracket_mask("a ([b c]) d")
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.tokens, ("a", "d"))
        self.assertEqual(candidate.restored_positions, ((), ()))
        self.assertTrue(candidate.brackets_omitted_with_parenthesis)

    def test_brackets_surviving_on_core_keep_character_positions(self):
        candidate = parenthesis_core_with_bracket_mask("[a] (b) c")
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.tokens, ("a", "c"))
        self.assertEqual(candidate.restored_positions, ((0,), ()))
        self.assertFalse(candidate.brackets_omitted_with_parenthesis)

    def test_opaque_bracket_slash_markup_entirely_inside_omitted_group_can_be_researched(self):
        candidate = opaque_parenthesis_core_with_inner_brackets("a ([b/c]) d")
        self.assertEqual(candidate, ("a", "d"))
        self.assertIsNone(
            opaque_parenthesis_core_with_inner_brackets("[a] (b/c) d")
        )
        self.assertIsNone(
            opaque_parenthesis_core_with_inner_brackets("a ([b]) d/e")
        )

    def test_crossing_or_mixed_slash_syntax_fails_closed(self):
        for value in ("[a (b]) c", "a ([b/c]) d", "a (b) [c"):
            with self.subTest(value=value):
                self.assertIsNone(parenthesis_core_with_bracket_mask(value))


class RestorationEvidenceTests(unittest.TestCase):
    def test_exact_partial_restoration_agreement(self):
        outcome = compare_cuc_restoration_mask(
            candidate_tokens=("abc",),
            restored_positions=((1,),),
            span=(100,),
            index=_index(),
            sign_values={1: "a", 2: "b", 3: "c", 4: "d", 5: "e"},
            sign_emen={2: "restored"},
            sign_cert={},
            sign_alt={},
        )
        self.assertEqual(outcome["restoration"], "exact")
        self.assertEqual(outcome["cert_values"], {})
        self.assertEqual(outcome["alt_values"], {})

    def test_missing_extra_and_sign_mapping_mismatch_are_distinct(self):
        missing = compare_cuc_restoration_mask(
            candidate_tokens=("abc",),
            restored_positions=((1,),),
            span=(100,),
            index=_index(),
            sign_values={1: "a", 2: "b", 3: "c", 4: "d", 5: "e"},
            sign_emen={},
            sign_cert={},
            sign_alt={},
        )
        self.assertEqual(missing["restoration"], "missing")

        extra = compare_cuc_restoration_mask(
            candidate_tokens=("abc",),
            restored_positions=((1,),),
            span=(100,),
            index=_index(),
            sign_values={1: "a", 2: "b", 3: "c", 4: "d", 5: "e"},
            sign_emen={2: "restored", 3: "restored"},
            sign_cert={},
            sign_alt={},
        )
        self.assertEqual(extra["restoration"], "extra")

        mismatch = compare_cuc_restoration_mask(
            candidate_tokens=("abc",),
            restored_positions=((1,),),
            span=(100,),
            index=_index(),
            sign_values={1: "a", 2: "x", 3: "c", 4: "d", 5: "e"},
            sign_emen={2: "restored"},
            sign_cert={},
            sign_alt={},
        )
        self.assertEqual(mismatch["restoration"], "sign_mapping_mismatch")

    def test_cert_and_alt_values_are_reported_not_interpreted(self):
        outcome = compare_cuc_restoration_mask(
            candidate_tokens=("abc",),
            restored_positions=((1,),),
            span=(100,),
            index=_index(),
            sign_values={1: "a", 2: "b", 3: "c", 4: "d", 5: "e"},
            sign_emen={2: "restored"},
            sign_cert={2: "True"},
            sign_alt={2: "x"},
        )
        self.assertEqual(outcome["restoration"], "exact")
        self.assertEqual(outcome["cert_values"], {"True": 1})
        self.assertEqual(outcome["alt_values"], {"x": 1})

    def test_payload_can_be_aggregated_without_lexical_text(self):
        outcome = compare_cuc_restoration_mask(
            candidate_tokens=("abc",),
            restored_positions=((0,),),
            span=(100,),
            index=_index(),
            sign_values={1: "a", 2: "b", 3: "c", 4: "d", 5: "e"},
            sign_emen={1: "restored"},
            sign_cert={1: "False"},
            sign_alt={},
        )
        payload = json.dumps(outcome, sort_keys=True)
        self.assertNotIn("abc", payload)
        self.assertNotIn("KTU", payload)


if __name__ == "__main__":
    unittest.main()
