from __future__ import annotations

import json
import unittest
from types import MappingProxyType

from scripts.audit_burns_alignment import aggregate_alignment_stats
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


def _source() -> NormalizedBurnsSource:
    record = BurnsSourceRecord(
        record_id="burns-record-sha256:r1",
        source_file="01 Restricted/Worksheet 1.pdf",
        source_row=1,
        source_page=7,
        section="Section α",
        root="secret-root",
        headword="secret-headword",
        ktu="1.14",
        references="I.3",
        locus="GP",
        room="restricted-room",
        point="",
        depth="",
        disputed="",
        comments="restricted comment text",
        worksheet_id="01 Restricted/Worksheet 1",
        workbook_number=1,
        workbook_label="01 Restricted",
        worksheet_number=1,
        worksheet_role=BurnsWorksheetRole.PRIME_GP,
        textual_status=BurnsTextualStatus.TEXTUAL,
        semantic_status=BurnsSemanticStatus.POSITIVE_FIXED,
        interpretive_status=BurnsInterpretiveStatus.UNSPECIFIED,
    )
    annotation = BurnsAnnotation(
        annotation_id="burns-annotation-sha256:a1",
        worksheet_id=record.worksheet_id,
        workbook_number=1,
        workbook_label="01 Restricted",
        worksheet_number=1,
        worksheet_role=BurnsWorksheetRole.PRIME_GP,
        first_source_row=1,
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
    return NormalizedBurnsSource(records=(record,), annotations=(annotation,))


def _alignment() -> BurnsAnnotationAlignment:
    target = BurnsTarget("KTU 1.14", "I", 3)
    parsed = ParsedBurnsReference(
        original_ktu="1.14",
        original_reference="I.3",
        status=BurnsReferenceStatus.PARSED,
        reason=BurnsReferenceReason.NONE,
        targets=(target,),
    )
    occurrence = BurnsAlignmentOccurrence(
        occurrence_id="burns-occurrence-sha256:o1",
        target_ordinal=0,
        target=target,
        disposition=BurnsAlignmentDisposition.ALIGNED,
        reason=BurnsAlignmentReason.NONE,
        confidence=BurnsAlignmentConfidence.EXACT_LEXICAL,
        anchor_kind=BurnsAnchorKind.WORD_SPAN,
        anchor_nodes=(300, 301),
        context_line_node=200,
    )
    return BurnsAnnotationAlignment(
        annotation_id="burns-annotation-sha256:a1",
        record_ids=("burns-record-sha256:r1",),
        parsed_reference=parsed,
        disposition=BurnsAlignmentDisposition.ALIGNED,
        reason=BurnsAlignmentReason.NONE,
        occurrences=(occurrence,),
    )


class AlignmentAuditAggregateTests(unittest.TestCase):
    def test_aggregate_output_contains_counts_only(self):
        source = _source()
        stats = aggregate_alignment_stats(
            file_count=45,
            source=source,
            alignments=(_alignment(),),
        )
        self.assertEqual(stats["source"], {"files": 45, "records": 1, "annotations": 1})
        self.assertEqual(stats["annotation_dispositions"], {"aligned": 1})
        self.assertEqual(stats["occurrence_dispositions"], {"aligned": 1})
        self.assertEqual(stats["occurrence_reasons"], {"none": 1})
        self.assertEqual(stats["anchor_kinds"], {"word_span": 1})
        self.assertEqual(stats["word_span_lengths"], {"2": 1})

        payload = json.dumps(stats, ensure_ascii=False, sort_keys=True)
        for restricted in (
            "secret-root",
            "secret-headword",
            "restricted-room",
            "restricted comment text",
            "01 Restricted/Worksheet 1.pdf",
            "I.3",
        ):
            self.assertNotIn(restricted, payload)

    def test_reference_failure_classification_is_aggregate_only(self):
        source = _source()
        private_locator = "III/4 secret-locator"
        parsed = ParsedBurnsReference(
            original_ktu="1.14",
            original_reference=private_locator,
            status=BurnsReferenceStatus.UNSUPPORTED,
            reason=BurnsReferenceReason.UNSUPPORTED_PUNCTUATION,
            targets=(),
        )
        failed = BurnsAnnotationAlignment(
            annotation_id="burns-annotation-sha256:a1",
            record_ids=("burns-record-sha256:r1",),
            parsed_reference=parsed,
            disposition=BurnsAlignmentDisposition.UNRESOLVED_REFERENCE,
            reason=BurnsAlignmentReason.REFERENCE_PARSE_FAILED,
            occurrences=(),
        )
        stats = aggregate_alignment_stats(
            file_count=45,
            source=source,
            alignments=(failed,),
        )
        self.assertEqual(stats["reference_statuses"], {"unsupported": 1})
        self.assertEqual(
            stats["reference_failure_reasons"],
            {"unsupported_punctuation": 1},
        )
        payload = json.dumps(stats, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(private_locator, payload)
        self.assertNotIn("1.14", payload)
        self.assertNotIn(failed.annotation_id, payload)

    def test_span_node_multiplicity_counts_selected_annotations_not_occurrence_repetition(self):
        source = _source()
        first = _alignment()
        second_occurrence = BurnsAlignmentOccurrence(
            occurrence_id="burns-occurrence-sha256:o2",
            target_ordinal=0,
            target=BurnsTarget("KTU 1.14", "I", 3),
            disposition=BurnsAlignmentDisposition.ALIGNED,
            reason=BurnsAlignmentReason.NONE,
            confidence=BurnsAlignmentConfidence.EXACT_LEXICAL,
            anchor_kind=BurnsAnchorKind.WORD_SPAN,
            anchor_nodes=(301, 302),
            context_line_node=200,
        )
        second = BurnsAnnotationAlignment(
            annotation_id="burns-annotation-sha256:a2",
            record_ids=("burns-record-sha256:r2",),
            parsed_reference=first.parsed_reference,
            disposition=BurnsAlignmentDisposition.ALIGNED,
            reason=BurnsAlignmentReason.NONE,
            occurrences=(second_occurrence,),
        )
        stats = aggregate_alignment_stats(
            file_count=45,
            source=source,
            alignments=(first, second),
        )
        self.assertEqual(
            stats["selected_anchor_node_multiplicity"],
            {"nodes_with_multiple_annotations": 1, "max_annotations_per_node": 2},
        )


if __name__ == "__main__":
    unittest.main()
