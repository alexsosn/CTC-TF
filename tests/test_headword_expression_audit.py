from __future__ import annotations

import json
import unittest
from dataclasses import replace

from scripts.audit_burns_alignment import (
    aggregate_headword_expression_stats,
    classify_headword_expression,
)
from ugarit_context_parsing.alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentDisposition,
    BurnsAlignmentOccurrence,
    BurnsAlignmentReason,
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
)
from ugarit_context_parsing.annotations import (
    BurnsAnnotation,
    BurnsInterpretiveStatus,
    BurnsSemanticStatus,
    BurnsSourceRecord,
    BurnsTextualStatus,
    BurnsWorksheetRole,
    NormalizedBurnsSource,
)
from ugarit_context_parsing.references import (
    BurnsReferenceReason,
    BurnsReferenceStatus,
    BurnsTarget,
    ParsedBurnsReference,
)


def _record(row: int, headword: str) -> BurnsSourceRecord:
    return BurnsSourceRecord(
        record_id=f"burns-record-sha256:r{row}",
        source_file="01 Restricted/Worksheet 1.pdf",
        source_row=row,
        source_page=7,
        section="Section α",
        root="private-root",
        headword=headword,
        ktu="1.14",
        references=f"I.{row}",
        locus="GP",
        room="private-room",
        point="",
        depth="",
        disputed="",
        comments="private-comment",
        worksheet_id="01 Restricted/Worksheet 1",
        workbook_number=1,
        workbook_label="01 Restricted",
        worksheet_number=1,
        worksheet_role=BurnsWorksheetRole.PRIME_GP,
        textual_status=BurnsTextualStatus.TEXTUAL,
        semantic_status=BurnsSemanticStatus.POSITIVE_FIXED,
        interpretive_status=BurnsInterpretiveStatus.UNSPECIFIED,
    )


def _annotation(record: BurnsSourceRecord) -> BurnsAnnotation:
    return BurnsAnnotation(
        annotation_id=f"burns-annotation-sha256:a{record.source_row}",
        worksheet_id=record.worksheet_id,
        workbook_number=record.workbook_number,
        workbook_label=record.workbook_label,
        worksheet_number=record.worksheet_number,
        worksheet_role=record.worksheet_role,
        first_source_row=record.source_row,
        section=record.section,
        root=record.root,
        headword=record.headword,
        ktu=record.ktu,
        references=record.references,
        textual_status=record.textual_status,
        semantic_status=record.semantic_status,
        interpretive_status=record.interpretive_status,
        record_ids=(record.record_id,),
    )


def _parsed(line: int | None) -> ParsedBurnsReference:
    return ParsedBurnsReference(
        original_ktu="1.14",
        original_reference="" if line is None else f"I.{line}",
        status=BurnsReferenceStatus.PARSED,
        reason=BurnsReferenceReason.NONE,
        targets=(BurnsTarget("KTU 1.14", "I" if line is not None else None, line),),
    )


def _alignment(
    annotation: BurnsAnnotation,
    *,
    line: int | None,
    reason: BurnsAlignmentReason,
    confidence: BurnsAlignmentConfidence,
    anchor_kind: BurnsAnchorKind,
) -> BurnsAnnotationAlignment:
    occurrence = BurnsAlignmentOccurrence(
        occurrence_id=f"burns-occurrence-sha256:o{annotation.first_source_row}",
        target_ordinal=0,
        target=_parsed(line).targets[0],
        disposition=(
            BurnsAlignmentDisposition.AMBIGUOUS
            if reason is BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN
            else BurnsAlignmentDisposition.ALIGNED
        ),
        reason=reason,
        confidence=confidence,
        anchor_kind=anchor_kind,
        anchor_nodes=(200 + annotation.first_source_row,),
        context_line_node=(200 + annotation.first_source_row if line is not None else None),
    )
    return BurnsAnnotationAlignment(
        annotation_id=annotation.annotation_id,
        record_ids=annotation.record_ids,
        parsed_reference=_parsed(line),
        disposition=occurrence.disposition,
        reason=reason if occurrence.disposition is not BurnsAlignmentDisposition.ALIGNED else BurnsAlignmentReason.NONE,
        occurrences=(occurrence,),
    )


class HeadwordExpressionClassifierTests(unittest.TestCase):
    def test_flags_are_independent_and_exclusive_bucket_has_documented_precedence(self):
        value = "private[alpha]/beta*"
        result = classify_headword_expression(value)
        self.assertEqual(
            result,
            {
                "parentheses": False,
                "square_brackets": True,
                "slash": True,
                "trailing_editorial_marker": True,
                "unbalanced_parentheses": False,
                "unbalanced_square_brackets": False,
                "parenthesis_shape": "none",
                "exclusive_class": "square_brackets",
            },
        )

    def test_parenthesis_shapes_are_structural_not_lexical(self):
        cases = {
            "private (alpha)": "trailing",
            "(private) alpha": "leading",
            "private (alpha) beta": "medial",
            "(private alpha)": "whole_expression",
            "private (alpha (beta))": "multiple_or_nested",
            "private (alpha": "unbalanced",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(
                    classify_headword_expression(value)["parenthesis_shape"],
                    expected,
                )

    def test_marker_only_and_clean_are_distinct(self):
        self.assertEqual(
            classify_headword_expression("private*")["exclusive_class"],
            "marker_only",
        )
        self.assertEqual(
            classify_headword_expression("private")["exclusive_class"],
            "clean",
        )


class HeadwordExpressionAggregateTests(unittest.TestCase):
    def test_occurrence_denominator_counts_only_exactly_resolved_lexical_context(self):
        records = (
            _record(1, "private (alpha)"),
            _record(2, "[private]"),
            _record(3, "private/alpha"),
            _record(4, "private*"),
        )
        annotations = tuple(_annotation(record) for record in records)
        source = NormalizedBurnsSource(records=records, annotations=annotations)
        alignments = (
            _alignment(
                annotations[0],
                line=1,
                reason=BurnsAlignmentReason.NONE,
                confidence=BurnsAlignmentConfidence.EXACT_LEXICAL,
                anchor_kind=BurnsAnchorKind.WORD_SPAN,
            ),
            _alignment(
                annotations[1],
                line=2,
                reason=BurnsAlignmentReason.HEADWORD_NOT_FOUND,
                confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
                anchor_kind=BurnsAnchorKind.LINE,
            ),
            _alignment(
                annotations[2],
                line=3,
                reason=BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN,
                confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
                anchor_kind=BurnsAnchorKind.LINE,
            ),
            # Tablet-only is structural evidence but has no lexical line context.
            _alignment(
                annotations[3],
                line=None,
                reason=BurnsAlignmentReason.NONE,
                confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
                anchor_kind=BurnsAnchorKind.TABLET,
            ),
        )

        stats = aggregate_headword_expression_stats(
            source=source,
            alignments=alignments,
        )

        self.assertEqual(stats["eligible_occurrences"], 3)
        self.assertEqual(
            stats["outcomes"],
            {"ambiguous_span": 1, "matched": 1, "not_found": 1},
        )
        self.assertEqual(
            stats["exclusive_classes"],
            {
                "parentheses": {"ambiguous_span": 0, "matched": 1, "not_found": 0, "occurrences": 1},
                "slash": {"ambiguous_span": 1, "matched": 0, "not_found": 0, "occurrences": 1},
                "square_brackets": {"ambiguous_span": 0, "matched": 0, "not_found": 1, "occurrences": 1},
            },
        )
        self.assertEqual(
            stats["flags"]["parentheses"],
            {"ambiguous_span": 0, "matched": 1, "not_found": 0, "occurrences": 1},
        )
        self.assertEqual(
            stats["flags"]["square_brackets"],
            {"ambiguous_span": 0, "matched": 0, "not_found": 1, "occurrences": 1},
        )
        self.assertEqual(
            stats["parenthesis_shapes"]["trailing"],
            {"ambiguous_span": 0, "matched": 1, "not_found": 0, "occurrences": 1},
        )

    def test_aggregate_payload_does_not_leak_source_strings(self):
        record = _record(1, "private (secret-headword)")
        annotation = _annotation(record)
        source = NormalizedBurnsSource(records=(record,), annotations=(annotation,))
        alignment = _alignment(
            annotation,
            line=1,
            reason=BurnsAlignmentReason.HEADWORD_NOT_FOUND,
            confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
            anchor_kind=BurnsAnchorKind.LINE,
        )
        payload = json.dumps(
            aggregate_headword_expression_stats(
                source=source,
                alignments=(alignment,),
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret-headword",
            "private-root",
            "private-room",
            "private-comment",
            "01 Restricted",
            "I.1",
            "1.14",
            annotation.annotation_id,
            record.record_id,
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
