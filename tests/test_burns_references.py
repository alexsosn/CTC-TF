from __future__ import annotations

import unittest

from ugarit_context_parsing.annotations import BurnsTextualStatus
from ugarit_context_parsing.references import (
    MAX_REFERENCE_RANGE_SPAN,
    BurnsReferenceReason,
    BurnsReferenceStatus,
    BurnsTarget,
    parse_burns_reference,
)


TEXTUAL = BurnsTextualStatus.TEXTUAL
NON_TEXTUAL = BurnsTextualStatus.NON_TEXTUAL_NOT_ATTESTED


def parse(ktu: str, reference: str, status: BurnsTextualStatus = TEXTUAL):
    return parse_burns_reference(
        ktu=ktu,
        reference=reference,
        textual_status=status,
    )


class BurnsReferenceParserTests(unittest.TestCase):
    def assert_parsed(self, result, targets: tuple[BurnsTarget, ...]) -> None:
        self.assertEqual(result.status, BurnsReferenceStatus.PARSED)
        self.assertEqual(result.reason, BurnsReferenceReason.NONE)
        self.assertEqual(result.targets, targets)

    def assert_rejected(
        self,
        result,
        status: BurnsReferenceStatus,
        reason: BurnsReferenceReason,
    ) -> None:
        self.assertEqual(result.status, status)
        self.assertEqual(result.reason, reason)
        self.assertEqual(result.targets, ())

    def test_valid_ktu_with_empty_reference_is_tablet_only(self):
        result = parse("1.14", "")
        self.assert_parsed(result, (BurnsTarget("KTU 1.14", None, None),))

    def test_single_arabic_line(self):
        result = parse("KTU 1.14", "3")
        self.assert_parsed(result, (BurnsTarget("KTU 1.14", None, 3),))

    def test_comma_list_preserves_authored_order(self):
        result = parse("1.14", "3, 5, 9")
        self.assert_parsed(
            result,
            (
                BurnsTarget("KTU 1.14", None, 3),
                BurnsTarget("KTU 1.14", None, 5),
                BurnsTarget("KTU 1.14", None, 9),
            ),
        )

    def test_inclusive_range_expands_in_order(self):
        result = parse("1.14", "3-5")
        self.assert_parsed(
            result,
            tuple(BurnsTarget("KTU 1.14", None, line) for line in (3, 4, 5)),
        )

    def test_list_and_range_mixture(self):
        result = parse("1.14", "1, 3-4, 7")
        self.assert_parsed(
            result,
            tuple(BurnsTarget("KTU 1.14", None, line) for line in (1, 3, 4, 7)),
        )

    def test_roman_column_qualifies_line(self):
        result = parse("1.14", "II.3")
        self.assert_parsed(result, (BurnsTarget("KTU 1.14", "II", 3),))

    def test_comma_continuations_inherit_column_inside_group(self):
        result = parse("1.14", "II.3, 4, 6-7")
        self.assert_parsed(
            result,
            tuple(
                BurnsTarget("KTU 1.14", "II", line)
                for line in (3, 4, 6, 7)
            ),
        )

    def test_semicolon_starts_new_explicit_column_group(self):
        result = parse("1.14", "II.3,4; III.1-2")
        self.assert_parsed(
            result,
            (
                BurnsTarget("KTU 1.14", "II", 3),
                BurnsTarget("KTU 1.14", "II", 4),
                BurnsTarget("KTU 1.14", "III", 1),
                BurnsTarget("KTU 1.14", "III", 2),
            ),
        )

    def test_comma_can_start_a_new_explicit_column_group(self):
        result = parse("1.14", "II.3, 4, III.1, 2")
        self.assert_parsed(
            result,
            (
                BurnsTarget("KTU 1.14", "II", 3),
                BurnsTarget("KTU 1.14", "II", 4),
                BurnsTarget("KTU 1.14", "III", 1),
                BurnsTarget("KTU 1.14", "III", 2),
            ),
        )

    def test_whitespace_is_ignored_only_for_parsing(self):
        original = " \n II . 3 , 4 ; III . 1 - 2 \t"
        result = parse("  KTU   1.14  ", original)
        self.assert_parsed(
            result,
            (
                BurnsTarget("KTU 1.14", "II", 3),
                BurnsTarget("KTU 1.14", "II", 4),
                BurnsTarget("KTU 1.14", "III", 1),
                BurnsTarget("KTU 1.14", "III", 2),
            ),
        )
        self.assertEqual(result.original_ktu, "  KTU   1.14  ")
        self.assertEqual(result.original_reference, original)

    def test_supported_ktu_suffix_is_retained(self):
        result = parse("2.105a", "1")
        self.assert_parsed(result, (BurnsTarget("KTU 2.105a", None, 1),))

    def test_non_textual_short_circuits_without_interpreting_reference(self):
        result = parse("Not attested (synthetic)", "prose 3?", NON_TEXTUAL)
        self.assert_rejected(
            result,
            BurnsReferenceStatus.NON_TEXTUAL,
            BurnsReferenceReason.NON_TEXTUAL,
        )
        self.assertEqual(result.original_ktu, "Not attested (synthetic)")
        self.assertEqual(result.original_reference, "prose 3?")

    def test_invalid_ktu_is_not_confused_with_cuc_membership(self):
        result = parse("see comments", "3")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.INVALID_KTU,
            BurnsReferenceReason.INVALID_KTU,
        )

    def test_syntactically_valid_unknown_tablet_still_parses(self):
        result = parse("999.999", "3")
        self.assert_parsed(result, (BurnsTarget("KTU 999.999", None, 3),))

    def test_prose_with_digits_does_not_partially_parse(self):
        result = parse("1.14", "compare line 3 above")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.UNSUPPORTED,
            BurnsReferenceReason.UNSUPPORTED_WORDING,
        )

    def test_uncertainty_marker_does_not_partially_parse(self):
        result = parse("1.14", "3?")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.UNSUPPORTED,
            BurnsReferenceReason.UNCERTAIN_MARKER,
        )

    def test_unsupported_punctuation_does_not_partially_parse(self):
        result = parse("1.14", "3/4")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.UNSUPPORTED,
            BurnsReferenceReason.UNSUPPORTED_PUNCTUATION,
        )

    def test_lowercase_roman_column_is_not_silently_normalized(self):
        result = parse("1.14", "ii.3")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.MALFORMED,
            BurnsReferenceReason.MALFORMED_STRUCTURE,
        )

    def test_missing_line_after_column_is_malformed(self):
        result = parse("1.14", "II.")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.MALFORMED,
            BurnsReferenceReason.MALFORMED_STRUCTURE,
        )

    def test_reversed_range_fails_closed(self):
        result = parse("1.14", "5-3")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.MALFORMED,
            BurnsReferenceReason.REVERSED_RANGE,
        )

    def test_exact_range_bound_is_allowed(self):
        start = 3
        end = start + MAX_REFERENCE_RANGE_SPAN
        result = parse("1.14", f"{start}-{end}")
        self.assertEqual(len(result.targets), MAX_REFERENCE_RANGE_SPAN + 1)
        self.assert_parsed(
            result,
            tuple(
                BurnsTarget("KTU 1.14", None, line)
                for line in range(start, end + 1)
            ),
        )

    def test_overlarge_range_fails_before_expansion(self):
        start = 3
        end = start + MAX_REFERENCE_RANGE_SPAN + 1
        result = parse("1.14", f"{start}-{end}")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.MALFORMED,
            BurnsReferenceReason.RANGE_TOO_LARGE,
        )

    def test_duplicate_target_is_not_silently_deduplicated(self):
        result = parse("1.14", "II.3, 3")
        self.assert_rejected(
            result,
            BurnsReferenceStatus.MALFORMED,
            BurnsReferenceReason.DUPLICATE_TARGET,
        )

    def test_original_strings_survive_rejection_exactly(self):
        ktu = " 1.14 "
        reference = "line 3?\n"
        result = parse(ktu, reference)
        self.assertEqual(result.original_ktu, ktu)
        self.assertEqual(result.original_reference, reference)


if __name__ == "__main__":
    unittest.main()
