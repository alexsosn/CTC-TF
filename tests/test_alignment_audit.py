from __future__ import annotations

import json
import unittest
from dataclasses import replace
from types import MappingProxyType

from scripts.audit_burns_alignment import aggregate_alignment_stats, aggregate_lexical_gap_stats
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
from ugarit_context_parsing.cuc_index import ReviewedCucIndex
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


def _gap_alignment() -> BurnsAnnotationAlignment:
    base = _alignment()
    occurrence = replace(
        base.occurrences[0],
        disposition=BurnsAlignmentDisposition.ALIGNED,
        reason=BurnsAlignmentReason.HEADWORD_NOT_FOUND,
        confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
        anchor_kind=BurnsAnchorKind.LINE,
        anchor_nodes=(200,),
        context_line_node=200,
    )
    return replace(base, occurrences=(occurrence,))


def _gap_index(*words: str) -> ReviewedCucIndex:
    nodes = tuple(range(300, 300 + len(words)))
    return ReviewedCucIndex(
        compatibility=None,
        tablet_nodes=MappingProxyType({"KTU 1.14": 100}),
        column_nodes=MappingProxyType({("KTU 1.14", "I"): 110}),
        line_nodes=MappingProxyType({("KTU 1.14", "I", 3): 200}),
        bare_line_candidates=MappingProxyType({("KTU 1.14", 3): (200,)}),
        line_words=MappingProxyType({200: nodes}),
        word_g_cons=MappingProxyType(dict(zip(nodes, words, strict=True))),
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


    def test_lexical_gap_audit_is_aggregate_only_and_classifies_prefix_candidate(self):
        source = _source()
        stats = aggregate_lexical_gap_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=_gap_index("secret-headwordm", "other-secret"),
        )
        self.assertEqual(
            stats,
            {
                "occurrences": 1,
                "headword_token_counts": {"1": 1},
                "line_word_counts": {"2": 1},
                "exact_token_overlap": {"none": 1},
                "single_token_prefix_candidates": {"1": 1},
                "single_token_suffix_candidates": {"0": 1},
                "single_token_contains_candidates": {"1": 1},
            },
        )
        payload = json.dumps(stats, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("secret-headword", payload)
        self.assertNotIn("secret-headwordm", payload)
        self.assertNotIn("other-secret", payload)

    def test_lexical_gap_audit_marks_exact_tokens_present_but_noncontiguous(self):
        original = _source()
        annotation = replace(original.annotations[0], headword="secret alpha")
        source = NormalizedBurnsSource(
            records=original.records,
            annotations=(annotation,),
        )
        stats = aggregate_lexical_gap_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=_gap_index("secret", "middle", "alpha"),
        )
        self.assertEqual(stats["exact_token_overlap"], {"all_present_noncontiguous_or_reordered": 1})
        self.assertEqual(stats["headword_token_counts"], {"2": 1})

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
        self.assertEqual(
            stats["reference_failure_shapes"],
            {"unsupported_punctuation|ktu=N.N|ref=R/N A-A": 1},
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
