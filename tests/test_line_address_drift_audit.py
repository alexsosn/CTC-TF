from __future__ import annotations

import json
import unittest
from dataclasses import replace
from types import MappingProxyType

from scripts.audit_burns_alignment import aggregate_line_address_drift_stats
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


def _source(headword: str = "secret-target") -> NormalizedBurnsSource:
    record = BurnsSourceRecord(
        record_id="burns-record-sha256:r1",
        source_file="01 Restricted/Worksheet 1.pdf",
        source_row=1,
        source_page=7,
        section="Section α",
        root="secret-root",
        headword=headword,
        ktu="1.14",
        references="I.3",
        locus="GP",
        room="secret-room",
        point="",
        depth="",
        disputed="",
        comments="secret-comment",
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
        workbook_number=record.workbook_number,
        workbook_label=record.workbook_label,
        worksheet_number=record.worksheet_number,
        worksheet_role=record.worksheet_role,
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


def _gap_alignment(
    *,
    column: str | None = "I",
    line: int = 3,
    annotation_id: str = "burns-annotation-sha256:a1",
    record_id: str = "burns-record-sha256:r1",
    context_line_node: int = 200,
) -> BurnsAnnotationAlignment:
    target = BurnsTarget("KTU 1.14", column, line)
    parsed = ParsedBurnsReference(
        original_ktu="1.14",
        original_reference=f"{column + '.' if column else ''}{line}",
        status=BurnsReferenceStatus.PARSED,
        reason=BurnsReferenceReason.NONE,
        targets=(target,),
    )
    occurrence = BurnsAlignmentOccurrence(
        occurrence_id=f"burns-occurrence-sha256:o:{annotation_id}:{line}",
        target_ordinal=0,
        target=target,
        disposition=BurnsAlignmentDisposition.ALIGNED,
        reason=BurnsAlignmentReason.HEADWORD_NOT_FOUND,
        confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
        anchor_kind=BurnsAnchorKind.LINE,
        anchor_nodes=(context_line_node,),
        context_line_node=context_line_node,
    )
    return BurnsAnnotationAlignment(
        annotation_id=annotation_id,
        record_ids=(record_id,),
        parsed_reference=parsed,
        disposition=BurnsAlignmentDisposition.ALIGNED,
        reason=BurnsAlignmentReason.NONE,
        occurrences=(occurrence,),
    )


def _index(lines: dict[tuple[str, str, int], tuple[str, ...]]) -> ReviewedCucIndex:
    line_nodes: dict[tuple[str, str, int], int] = {}
    line_words: dict[int, tuple[int, ...]] = {}
    word_g_cons: dict[int, str] = {}
    bare: dict[tuple[str, int], list[int]] = {}
    columns: dict[tuple[str, str], int] = {}
    tablets: dict[str, int] = {}
    next_line = 200
    next_word = 300
    next_column = 100
    next_tablet = 50

    for key, words in sorted(lines.items()):
        tablet, column, line = key
        if tablet not in tablets:
            tablets[tablet] = next_tablet
            next_tablet += 1
        if (tablet, column) not in columns:
            columns[(tablet, column)] = next_column
            next_column += 1
        # Keep KTU 1.14 I.3 stable at node 200 because the alignment fixture uses it.
        if key == ("KTU 1.14", "I", 3):
            node = 200
        else:
            next_line += 1
            while next_line == 200 or next_line in line_nodes.values():
                next_line += 1
            node = next_line
        wn: list[int] = []
        for value in words:
            while next_word in word_g_cons:
                next_word += 1
            wn.append(next_word)
            word_g_cons[next_word] = value
            next_word += 1
        line_nodes[key] = node
        line_words[node] = tuple(wn)
        bare.setdefault((tablet, line), []).append(node)

    return ReviewedCucIndex(
        compatibility=None,
        tablet_nodes=MappingProxyType(tablets),
        column_nodes=MappingProxyType(columns),
        line_nodes=MappingProxyType(line_nodes),
        bare_line_candidates=MappingProxyType(
            {key: tuple(nodes) for key, nodes in bare.items()}
        ),
        line_words=MappingProxyType(line_words),
        word_g_cons=MappingProxyType(word_g_cons),
    )


class LineAddressDriftAuditTests(unittest.TestCase):
    def test_unique_plus_one_rescue(self):
        source = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 2): ("other",),
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret-target",),
                ("KTU 1.14", "I", 5): ("other",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["occurrences"], 1)
        self.assertEqual(stats["outcomes"], {"unique_neighbor": 1})
        self.assertEqual(stats["matched_neighbor_offsets"], {"+1": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {"+1": 1})


    def test_unique_minus_one_rescue(self):
        source = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 1): ("other",),
                ("KTU 1.14", "I", 2): ("secret-target",),
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("other",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"unique_neighbor": 1})
        self.assertEqual(stats["matched_neighbor_offsets"], {"-1": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {"-1": 1})

    def test_parenthesis_core_candidate_can_rescue_neighbor(self):
        source = _source("secret-target (optional)")
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret-target",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"unique_neighbor": 1})
        self.assertEqual(stats["matched_neighbor_offsets"], {"+1": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {"+1": 1})

    def test_slash_candidates_union_distinct_neighbor_spans_as_ambiguity(self):
        source = _source("secret/alternate")
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret", "alternate"),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"ambiguous_neighbor_span": 1})
        self.assertEqual(stats["matched_neighbor_offsets"], {"+1": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {})

    def test_opaque_parenthesis_core_candidate_can_rescue_neighbor(self):
        source = _source("secret-target ([restored]/alternate)")
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret-target",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"unique_neighbor": 1})
        self.assertEqual(stats["matched_neighbor_offsets"], {"+1": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {"+1": 1})

    def test_multiple_neighbor_offsets_are_not_a_unique_rescue(self):
        source = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 1): ("secret-target",),
                ("KTU 1.14", "I", 2): ("other",),
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret-target",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"multi_neighbor": 1})
        self.assertEqual(
            stats["matched_neighbor_offsets"],
            {"-2": 1, "+1": 1},
        )
        self.assertEqual(stats["unique_rescue_offsets"], {})

    def test_multiple_spans_on_one_neighbor_are_ambiguous(self):
        source = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret-target", "x", "secret-target"),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"ambiguous_neighbor_span": 1})
        self.assertEqual(stats["matched_neighbor_offsets"], {"+1": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {})

    def test_no_match_and_missing_neighbors_are_accounted_without_error(self):
        source = _source()
        index = _index({("KTU 1.14", "I", 3): ("wrong",)})
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"no_neighbor_match": 1})
        self.assertEqual(stats["available_neighbor_offsets"], {})
        self.assertEqual(stats["matched_neighbor_offsets"], {})

    def test_never_crosses_column_or_tablet_boundaries(self):
        source = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "II", 4): ("secret-target",),
                ("KTU 9.9", "I", 4): ("secret-target",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"no_neighbor_match": 1})
        self.assertEqual(stats["available_neighbor_offsets"], {})

    def test_bare_line_uses_resolved_context_node_identity(self):
        source = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong",),
                ("KTU 1.14", "I", 4): ("secret-target",),
                ("KTU 1.14", "II", 3): ("different",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(_gap_alignment(column=None),),
            index=index,
        )
        self.assertEqual(stats["outcomes"], {"unique_neighbor": 1})
        self.assertEqual(stats["unique_rescue_offsets"], {"+1": 1})

    def test_non_gap_occurrence_is_excluded(self):
        source = _source()
        gap = _gap_alignment()
        occurrence = replace(
            gap.occurrences[0],
            reason=BurnsAlignmentReason.NONE,
            confidence=BurnsAlignmentConfidence.EXACT_LEXICAL,
            anchor_kind=BurnsAnchorKind.WORD_SPAN,
            anchor_nodes=(300,),
        )
        aligned = replace(gap, occurrences=(occurrence,))
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("secret-target",),
                ("KTU 1.14", "I", 4): ("secret-target",),
            }
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=(aligned,),
            index=index,
        )
        self.assertEqual(stats["occurrences"], 0)
        self.assertEqual(stats["outcomes"], {})

    def test_unique_rescue_run_histogram_splits_on_line_gap(self):
        base = _source()
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong-3",),
                ("KTU 1.14", "I", 4): ("target-3",),
                ("KTU 1.14", "I", 5): ("target-4",),
                ("KTU 1.14", "I", 6): ("wrong-6",),
                ("KTU 1.14", "I", 7): ("target-6",),
            }
        )

        records = []
        annotations = []
        alignments = []
        for ordinal, line in enumerate((3, 4, 6), start=1):
            record_id = f"burns-record-sha256:r{ordinal}"
            annotation_id = f"burns-annotation-sha256:a{ordinal}"
            headword = f"target-{line}"
            record = replace(
                base.records[0],
                record_id=record_id,
                source_row=ordinal,
                headword=headword,
                references=f"I.{line}",
            )
            annotation = replace(
                base.annotations[0],
                annotation_id=annotation_id,
                first_source_row=ordinal,
                headword=headword,
                references=f"I.{line}",
                record_ids=(record_id,),
            )
            node = index.line_nodes[("KTU 1.14", "I", line)]
            records.append(record)
            annotations.append(annotation)
            alignments.append(
                _gap_alignment(
                    line=line,
                    annotation_id=annotation_id,
                    record_id=record_id,
                    context_line_node=node,
                )
            )

        source = NormalizedBurnsSource(
            records=tuple(records),
            annotations=tuple(annotations),
        )
        stats = aggregate_line_address_drift_stats(
            source=source,
            alignments=tuple(alignments),
            index=index,
        )
        self.assertEqual(stats["unique_rescue_offsets"], {"+1": 3})
        self.assertEqual(
            stats["unique_rescue_run_lengths"],
            {"+1": {"1": 1, "2": 1}},
        )

    def test_payload_is_source_safe(self):
        source = _source("secret-target")
        index = _index(
            {
                ("KTU 1.14", "I", 3): ("wrong-secret",),
                ("KTU 1.14", "I", 4): ("secret-target",),
            }
        )
        payload = json.dumps(
            aggregate_line_address_drift_stats(
                source=source,
                alignments=(_gap_alignment(),),
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret-target",
            "wrong-secret",
            "secret-root",
            "secret-room",
            "secret-comment",
            "KTU 1.14",
            "I.3",
            "burns-annotation",
            "burns-occurrence",
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
