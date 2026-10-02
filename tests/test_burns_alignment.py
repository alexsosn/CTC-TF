from __future__ import annotations

import unittest
from types import MappingProxyType

from ugarit_context_parsing.alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentDisposition,
    BurnsAlignmentReason,
    BurnsAnchorKind,
    align_burns_annotation,
    align_burns_source,
)
from ugarit_context_parsing.annotations import (
    BurnsAnnotation,
    BurnsInterpretiveStatus,
    BurnsSemanticStatus,
    BurnsTextualStatus,
    BurnsWorksheetRole,
    NormalizedBurnsSource,
)
from ugarit_context_parsing.cuc_index import ReviewedCucIndex
from ugarit_context_parsing.references import BurnsReferenceReason


def annotation(
    *,
    annotation_id: str = "burns-annotation-sha256:a",
    record_ids: tuple[str, ...] = ("burns-record-sha256:r1",),
    headword: str = "bʿl",
    ktu: str = "1.14",
    references: str = "I.1",
    textual_status: BurnsTextualStatus = BurnsTextualStatus.TEXTUAL,
) -> BurnsAnnotation:
    return BurnsAnnotation(
        annotation_id=annotation_id,
        worksheet_id="01 Synthetic/Worksheet 1",
        workbook_number=1,
        workbook_label="01 Synthetic",
        worksheet_number=1,
        worksheet_role=BurnsWorksheetRole.PRIME_GP,
        first_source_row=1,
        section="Section α",
        root="",
        headword=headword,
        ktu=ktu,
        references=references,
        textual_status=textual_status,
        semantic_status=BurnsSemanticStatus.POSITIVE_FIXED,
        interpretive_status=BurnsInterpretiveStatus.UNSPECIFIED,
        record_ids=record_ids,
    )


def synthetic_index() -> ReviewedCucIndex:
    return ReviewedCucIndex(
        compatibility=None,
        tablet_nodes=MappingProxyType({"KTU 1.14": 100}),
        column_nodes=MappingProxyType(
            {
                ("KTU 1.14", "I"): 110,
                ("KTU 1.14", "II"): 111,
            }
        ),
        line_nodes=MappingProxyType(
            {
                ("KTU 1.14", "I", 1): 200,
                ("KTU 1.14", "II", 1): 201,
                ("KTU 1.14", "I", 2): 202,
                ("KTU 1.14", "I", 3): 203,
                ("KTU 1.14", "I", 4): 204,
                ("KTU 1.14", "I", 5): 205,
                ("KTU 1.14", "I", 6): 206,
            }
        ),
        bare_line_candidates=MappingProxyType(
            {
                ("KTU 1.14", 1): (200, 201),
                ("KTU 1.14", 2): (202,),
                ("KTU 1.14", 3): (203,),
                ("KTU 1.14", 4): (204,),
                ("KTU 1.14", 5): (205,),
                ("KTU 1.14", 6): (206,),
            }
        ),
        line_words=MappingProxyType(
            {
                200: (300, 301, 302, 303),
                201: (304, 305),
                202: (310, 311, 312),
                203: (320, 321, 322, 323),
                204: (330, 331, 332, 333),
                205: (340, 341, 342),
                206: (350, 351, 352),
            }
        ),
        word_g_cons=MappingProxyType(
            {
                300: "w",
                301: "bʿl",
                302: "mlk",
                303: "ym",
                304: "bʿl",
                305: "x",
                310: "w",
                311: "bʿl",
                312: "x",
                320: "bʿl",
                321: "mlk",
                322: "w",
                323: "x",
                330: "bʿl",
                331: "x",
                332: "bʿl",
                333: "x",
                340: "bʿl",
                341: "",
                342: "mlk",
                350: "bʿl?",
                351: "x",
                352: "y",
            }
        ),
    )


class BurnsAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.index = synthetic_index()

    def test_non_textual_annotation_has_no_occurrences(self):
        result = align_burns_annotation(
            annotation(
                ktu="Not attested",
                references="unparsed prose 7",
                textual_status=BurnsTextualStatus.NON_TEXTUAL_NOT_ATTESTED,
            ),
            self.index,
        )
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.NON_TEXTUAL)
        self.assertEqual(result.reason, BurnsAlignmentReason.NON_TEXTUAL)
        self.assertEqual(result.occurrences, ())

    def test_valid_tablet_absent_from_cuc_is_out_of_cuc(self):
        result = align_burns_annotation(annotation(ktu="9.99", references="1"), self.index)
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.OUT_OF_CUC)
        self.assertEqual(result.reason, BurnsAlignmentReason.TABLET_NOT_IN_CUC)
        self.assertEqual(result.occurrences, ())

    def test_failed_reference_parse_is_preserved_and_unresolved(self):
        result = align_burns_annotation(annotation(references="3?"), self.index)
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.UNRESOLVED_REFERENCE)
        self.assertEqual(result.reason, BurnsAlignmentReason.REFERENCE_PARSE_FAILED)
        self.assertEqual(result.parsed_reference.reason, BurnsReferenceReason.UNCERTAIN_MARKER)
        self.assertEqual(result.occurrences, ())

    def test_tablet_only_target_selects_exact_structural_tablet(self):
        result = align_burns_annotation(annotation(references=""), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.ALIGNED)
        self.assertEqual(occurrence.disposition, BurnsAlignmentDisposition.ALIGNED)
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_STRUCTURAL)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.TABLET)
        self.assertEqual(occurrence.anchor_nodes, (100,))
        self.assertIsNone(occurrence.context_line_node)

    def test_explicit_line_is_narrowed_to_unique_word(self):
        result = align_burns_annotation(annotation(references="I.1", headword="bʿl"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
        self.assertEqual(occurrence.anchor_nodes, (301,))
        self.assertEqual(occurrence.context_line_node, 200)
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_LEXICAL)

    def test_unique_bare_line_resolves_without_guessing_column(self):
        result = align_burns_annotation(annotation(references="2", headword="bʿl"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.context_line_node, 202)
        self.assertEqual(occurrence.anchor_nodes, (311,))

    def test_ambiguous_bare_line_keeps_every_candidate_and_selects_none(self):
        result = align_burns_annotation(annotation(references="1"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.AMBIGUOUS)
        self.assertEqual(occurrence.disposition, BurnsAlignmentDisposition.AMBIGUOUS)
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.AMBIGUOUS_LINE)
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.NONE)
        self.assertIsNone(occurrence.anchor_kind)
        self.assertEqual(occurrence.anchor_nodes, ())
        self.assertEqual(occurrence.candidate_line_nodes, (200, 201))

    def test_missing_explicit_line_is_unresolved_without_tablet_fallback(self):
        result = align_burns_annotation(annotation(references="I.99"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.UNRESOLVED_REFERENCE)
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.LINE_NOT_FOUND)
        self.assertIsNone(occurrence.anchor_kind)
        self.assertEqual(occurrence.anchor_nodes, ())

    def test_unique_contiguous_multiword_match_is_one_ordered_span(self):
        result = align_burns_annotation(
            annotation(references="I.3", headword="bʿl mlk"),
            self.index,
        )
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
        self.assertEqual(occurrence.anchor_nodes, (320, 321))
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_LEXICAL)

    def test_repeated_lexical_match_keeps_safe_line_and_all_candidate_spans(self):
        result = align_burns_annotation(annotation(references="I.4", headword="bʿl"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.AMBIGUOUS)
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(occurrence.anchor_nodes, (204,))
        self.assertEqual(occurrence.context_line_node, 204)
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_STRUCTURAL)
        self.assertEqual(occurrence.candidate_spans, ((330,), (332,)))

    def test_discontinuous_tokens_do_not_manufacture_a_word_span(self):
        result = align_burns_annotation(
            annotation(references="I.5", headword="bʿl mlk"),
            self.index,
        )
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.HEADWORD_NOT_FOUND)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(occurrence.anchor_nodes, (205,))
        self.assertEqual(occurrence.candidate_spans, ())

    def test_simple_parenthesized_qualifier_is_omitted_for_exact_matching(self):
        result = align_burns_annotation(
            annotation(references="I.2", headword="bʿl (mlk)"),
            self.index,
        )
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
        self.assertEqual(occurrence.anchor_nodes, (311,))
        self.assertEqual(
            occurrence.candidate_matches,
            (("parenthesis_omit", (311,)),),
        )

    def test_parenthesized_group_is_not_an_optional_include_candidate(self):
        result = align_burns_annotation(
            annotation(references="I.3", headword="bʿl (mlk)"),
            self.index,
        )
        occurrence = result.occurrences[0]
        # Both bʿl and bʿl mlk occur on this line. Real-source research shows
        # include-group never independently rescues an occurrence, so the
        # supported surface candidate is the omit-group form only.
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
        self.assertEqual(occurrence.anchor_nodes, (320,))
        self.assertEqual(
            occurrence.candidate_matches,
            (("parenthesis_omit", (320,)),),
        )

    def test_include_only_parenthesized_surface_does_not_manufacture_match(self):
        result = align_burns_annotation(
            annotation(references="I.3", headword="bʿl (mlk) x"),
            self.index,
        )
        occurrence = result.occurrences[0]
        # The literal de-parenthesized string bʿl mlk x exists, but the
        # evidenced omit-group candidate bʿl x does not occur contiguously.
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.HEADWORD_NOT_FOUND)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(occurrence.anchor_nodes, (203,))
        self.assertEqual(occurrence.candidate_matches, ())

    def test_simple_slash_left_and_right_branches_can_match_exactly(self):
        left = align_burns_annotation(
            annotation(references="I.2", headword="bʿl/qrb"),
            self.index,
        ).occurrences[0]
        right = align_burns_annotation(
            annotation(references="I.2", headword="qrb/bʿl"),
            self.index,
        ).occurrences[0]
        self.assertEqual(left.anchor_nodes, (311,))
        self.assertEqual(right.anchor_nodes, (311,))
        self.assertEqual(left.candidate_matches, (("slash_left", (311,)),))
        self.assertEqual(right.candidate_matches, (("slash_right", (311,)),))

    def test_simple_slash_distinct_branches_remain_explicit_ambiguity(self):
        result = align_burns_annotation(
            annotation(references="I.3", headword="bʿl/mlk"),
            self.index,
        )
        occurrence = result.occurrences[0]
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.AMBIGUOUS)
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(occurrence.anchor_nodes, (203,))
        self.assertEqual(occurrence.candidate_spans, ((320,), (321,)))
        self.assertEqual(
            occurrence.candidate_matches,
            (
                ("slash_left", (320,)),
                ("slash_right", (321,)),
            ),
        )

    def test_simple_slash_candidates_converging_on_same_span_are_deduplicated(self):
        result = align_burns_annotation(
            annotation(references="I.2", headword="bʿl/bʿl"),
            self.index,
        )
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.WORD_SPAN)
        self.assertEqual(occurrence.anchor_nodes, (311,))
        self.assertEqual(
            occurrence.candidate_matches,
            (
                ("slash_left", (311,)),
                ("slash_right", (311,)),
            ),
        )

    def test_complex_or_cross_ticket_expression_syntax_still_fails_closed(self):
        for headword in (
            "bʿl/mlk/x",
            "bʿl / mlk",
            "bʿl (mlk) (x)",
            "[bʿl]",
        ):
            with self.subTest(headword=headword):
                occurrence = align_burns_annotation(
                    annotation(references="I.3", headword=headword),
                    self.index,
                ).occurrences[0]
                self.assertEqual(
                    occurrence.reason,
                    BurnsAlignmentReason.HEADWORD_NOT_FOUND,
                )
                self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
                self.assertEqual(occurrence.candidate_matches, ())

    def test_documented_trailing_editorial_markers_are_ignored_for_matching_only(self):
        source = annotation(references="I.3", headword="bʿl* mlk†")
        result = align_burns_annotation(source, self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(source.headword, "bʿl* mlk†")
        self.assertEqual(occurrence.anchor_nodes, (320, 321))

    def test_arbitrary_punctuation_is_not_removed_to_manufacture_match(self):
        result = align_burns_annotation(annotation(references="I.6", headword="bʿl,"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.HEADWORD_NOT_FOUND)
        self.assertEqual(occurrence.anchor_nodes, (206,))

    def test_empty_headword_keeps_exact_line_as_structural_anchor(self):
        result = align_burns_annotation(annotation(references="I.3", headword=""), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.EMPTY_HEADWORD)
        self.assertEqual(occurrence.anchor_kind, BurnsAnchorKind.LINE)
        self.assertEqual(occurrence.anchor_nodes, (203,))

    def test_zero_lexical_match_keeps_exact_line_as_structural_anchor(self):
        result = align_burns_annotation(annotation(references="I.3", headword="qrb"), self.index)
        occurrence = result.occurrences[0]
        self.assertEqual(occurrence.reason, BurnsAlignmentReason.HEADWORD_NOT_FOUND)
        self.assertEqual(occurrence.anchor_nodes, (203,))
        self.assertEqual(occurrence.confidence, BurnsAlignmentConfidence.EXACT_STRUCTURAL)

    def test_multiple_targets_preserve_authored_order_and_stable_occurrence_ids(self):
        source = annotation(references="I.2,3", headword="bʿl")
        first = align_burns_annotation(source, self.index)
        second = align_burns_annotation(source, self.index)
        self.assertEqual(first, second)
        self.assertEqual([item.target_ordinal for item in first.occurrences], [0, 1])
        self.assertNotEqual(first.occurrences[0].occurrence_id, first.occurrences[1].occurrence_id)
        for item in first.occurrences:
            self.assertTrue(item.occurrence_id.startswith("burns-occurrence-sha256:"))
            self.assertEqual(len(item.occurrence_id.split(":", 1)[1]), 64)

    def test_mixed_resolved_and_missing_targets_is_partial_without_losing_success(self):
        result = align_burns_annotation(annotation(references="I.2,99", headword="bʿl"), self.index)
        self.assertEqual(result.disposition, BurnsAlignmentDisposition.PARTIAL)
        self.assertEqual(result.reason, BurnsAlignmentReason.MIXED_TARGET_RESULTS)
        self.assertEqual(result.occurrences[0].anchor_nodes, (311,))
        self.assertEqual(result.occurrences[1].reason, BurnsAlignmentReason.LINE_NOT_FOUND)
        self.assertEqual(result.occurrences[1].anchor_nodes, ())

    def test_overlapping_annotations_are_never_merged_globally(self):
        longer = annotation(
            annotation_id="burns-annotation-sha256:long",
            record_ids=("burns-record-sha256:r1",),
            references="I.3",
            headword="bʿl mlk",
        )
        shorter = annotation(
            annotation_id="burns-annotation-sha256:short",
            record_ids=("burns-record-sha256:r2",),
            references="I.3",
            headword="mlk",
        )
        source = NormalizedBurnsSource(records=(), annotations=(longer, shorter))
        results = align_burns_source(source, self.index)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].occurrences[0].anchor_nodes, (320, 321))
        self.assertEqual(results[1].occurrences[0].anchor_nodes, (321,))
        self.assertNotEqual(results[0].annotation_id, results[1].annotation_id)


if __name__ == "__main__":
    unittest.main()
