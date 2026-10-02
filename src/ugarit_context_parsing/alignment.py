from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from .annotations import BurnsAnnotation, NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex
from .headword_expression import (
    headword_candidate_token_sets,
    literal_headword_tokens,
    nfc,
)
from .references import (
    BurnsReferenceStatus,
    BurnsTarget,
    ParsedBurnsReference,
    parse_burns_reference,
)

class BurnsAlignmentDisposition(str, Enum):
    ALIGNED = "aligned"
    AMBIGUOUS = "ambiguous"
    PARTIAL = "partial"
    UNRESOLVED_REFERENCE = "unresolved_reference"
    OUT_OF_CUC = "out_of_cuc"
    NON_TEXTUAL = "non_textual"


class BurnsAlignmentReason(str, Enum):
    NONE = "none"
    NON_TEXTUAL = "non_textual"
    TABLET_NOT_IN_CUC = "tablet_not_in_cuc"
    REFERENCE_PARSE_FAILED = "reference_parse_failed"
    LINE_NOT_FOUND = "line_not_found"
    AMBIGUOUS_LINE = "ambiguous_line"
    HEADWORD_NOT_FOUND = "headword_not_found"
    EMPTY_HEADWORD = "empty_headword"
    AMBIGUOUS_HEADWORD_SPAN = "ambiguous_headword_span"
    MIXED_TARGET_RESULTS = "mixed_target_results"


class BurnsAlignmentConfidence(str, Enum):
    EXACT_LEXICAL = "exact_lexical"
    EXACT_STRUCTURAL = "exact_structural"
    NONE = "none"


class BurnsAnchorKind(str, Enum):
    TABLET = "tablet"
    LINE = "line"
    WORD_SPAN = "word_span"


@dataclass(frozen=True)
class BurnsAlignmentOccurrence:
    occurrence_id: str
    target_ordinal: int
    target: BurnsTarget
    disposition: BurnsAlignmentDisposition
    reason: BurnsAlignmentReason
    confidence: BurnsAlignmentConfidence
    anchor_kind: BurnsAnchorKind | None
    anchor_nodes: tuple[int, ...]
    context_line_node: int | None
    candidate_line_nodes: tuple[int, ...] = ()
    candidate_spans: tuple[tuple[int, ...], ...] = ()


@dataclass(frozen=True)
class BurnsAnnotationAlignment:
    annotation_id: str
    record_ids: tuple[str, ...]
    parsed_reference: ParsedBurnsReference
    disposition: BurnsAlignmentDisposition
    reason: BurnsAlignmentReason
    occurrences: tuple[BurnsAlignmentOccurrence, ...]


def _nfc(value: str) -> str:
    return nfc(value)


def _occurrence_id(annotation_id: str, ordinal: int, target: BurnsTarget) -> str:
    payload = {
        "schema": "burns-alignment-occurrence-v1",
        "annotation_id": _nfc(annotation_id),
        "target_ordinal": ordinal,
        "target": {
            "tablet": _nfc(target.tablet),
            "column": _nfc(target.column) if target.column is not None else None,
            "line": target.line,
        },
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "burns-occurrence-sha256:" + hashlib.sha256(canonical).hexdigest()


def _headword_tokens(headword: str) -> tuple[str, ...]:
    """Compatibility wrapper for the historical literal tokenizer."""

    return literal_headword_tokens(headword)


def _candidate_spans(
    tokens: tuple[str, ...],
    line_node: int,
    index: ReviewedCucIndex,
) -> tuple[tuple[int, ...], ...]:
    words = index.line_words[line_node]
    width = len(tokens)
    if width == 0 or width > len(words):
        return ()

    values = tuple(_nfc(index.word_g_cons[word]) for word in words)
    matches: list[tuple[int, ...]] = []
    for start in range(len(words) - width + 1):
        if values[start : start + width] == tokens:
            matches.append(tuple(words[start : start + width]))
    return tuple(matches)


def _line_occurrence(
    annotation: BurnsAnnotation,
    target: BurnsTarget,
    ordinal: int,
    line_node: int,
    index: ReviewedCucIndex,
) -> BurnsAlignmentOccurrence:
    occurrence_id = _occurrence_id(annotation.annotation_id, ordinal, target)
    tokens = _headword_tokens(annotation.headword)
    if not tokens:
        return BurnsAlignmentOccurrence(
            occurrence_id=occurrence_id,
            target_ordinal=ordinal,
            target=target,
            disposition=BurnsAlignmentDisposition.ALIGNED,
            reason=BurnsAlignmentReason.EMPTY_HEADWORD,
            confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
            anchor_kind=BurnsAnchorKind.LINE,
            anchor_nodes=(line_node,),
            context_line_node=line_node,
        )

    candidate_tokens = headword_candidate_token_sets(annotation.headword)
    spans = tuple(
        dict.fromkeys(
            span
            for candidate in candidate_tokens
            for span in _candidate_spans(candidate, line_node, index)
        )
    )
    if len(spans) == 1:
        return BurnsAlignmentOccurrence(
            occurrence_id=occurrence_id,
            target_ordinal=ordinal,
            target=target,
            disposition=BurnsAlignmentDisposition.ALIGNED,
            reason=BurnsAlignmentReason.NONE,
            confidence=BurnsAlignmentConfidence.EXACT_LEXICAL,
            anchor_kind=BurnsAnchorKind.WORD_SPAN,
            anchor_nodes=spans[0],
            context_line_node=line_node,
        )
    if len(spans) > 1:
        return BurnsAlignmentOccurrence(
            occurrence_id=occurrence_id,
            target_ordinal=ordinal,
            target=target,
            disposition=BurnsAlignmentDisposition.AMBIGUOUS,
            reason=BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN,
            confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
            anchor_kind=BurnsAnchorKind.LINE,
            anchor_nodes=(line_node,),
            context_line_node=line_node,
            candidate_spans=spans,
        )
    return BurnsAlignmentOccurrence(
        occurrence_id=occurrence_id,
        target_ordinal=ordinal,
        target=target,
        disposition=BurnsAlignmentDisposition.ALIGNED,
        reason=BurnsAlignmentReason.HEADWORD_NOT_FOUND,
        confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
        anchor_kind=BurnsAnchorKind.LINE,
        anchor_nodes=(line_node,),
        context_line_node=line_node,
    )


def _resolve_target(
    annotation: BurnsAnnotation,
    target: BurnsTarget,
    ordinal: int,
    index: ReviewedCucIndex,
) -> BurnsAlignmentOccurrence:
    occurrence_id = _occurrence_id(annotation.annotation_id, ordinal, target)

    if target.line is None:
        return BurnsAlignmentOccurrence(
            occurrence_id=occurrence_id,
            target_ordinal=ordinal,
            target=target,
            disposition=BurnsAlignmentDisposition.ALIGNED,
            reason=BurnsAlignmentReason.NONE,
            confidence=BurnsAlignmentConfidence.EXACT_STRUCTURAL,
            anchor_kind=BurnsAnchorKind.TABLET,
            anchor_nodes=(index.tablet_nodes[target.tablet],),
            context_line_node=None,
        )

    if target.column is not None:
        line_node = index.line_nodes.get((target.tablet, target.column, target.line))
        if line_node is None:
            return BurnsAlignmentOccurrence(
                occurrence_id=occurrence_id,
                target_ordinal=ordinal,
                target=target,
                disposition=BurnsAlignmentDisposition.UNRESOLVED_REFERENCE,
                reason=BurnsAlignmentReason.LINE_NOT_FOUND,
                confidence=BurnsAlignmentConfidence.NONE,
                anchor_kind=None,
                anchor_nodes=(),
                context_line_node=None,
            )
        return _line_occurrence(annotation, target, ordinal, line_node, index)

    candidates = index.bare_line_candidates.get((target.tablet, target.line), ())
    if not candidates:
        return BurnsAlignmentOccurrence(
            occurrence_id=occurrence_id,
            target_ordinal=ordinal,
            target=target,
            disposition=BurnsAlignmentDisposition.UNRESOLVED_REFERENCE,
            reason=BurnsAlignmentReason.LINE_NOT_FOUND,
            confidence=BurnsAlignmentConfidence.NONE,
            anchor_kind=None,
            anchor_nodes=(),
            context_line_node=None,
        )
    if len(candidates) > 1:
        return BurnsAlignmentOccurrence(
            occurrence_id=occurrence_id,
            target_ordinal=ordinal,
            target=target,
            disposition=BurnsAlignmentDisposition.AMBIGUOUS,
            reason=BurnsAlignmentReason.AMBIGUOUS_LINE,
            confidence=BurnsAlignmentConfidence.NONE,
            anchor_kind=None,
            anchor_nodes=(),
            context_line_node=None,
            candidate_line_nodes=tuple(candidates),
        )
    return _line_occurrence(annotation, target, ordinal, candidates[0], index)


def _summarize_occurrences(
    occurrences: tuple[BurnsAlignmentOccurrence, ...],
) -> tuple[BurnsAlignmentDisposition, BurnsAlignmentReason]:
    dispositions = tuple(item.disposition for item in occurrences)
    reasons = tuple(item.reason for item in occurrences)

    if all(item is BurnsAlignmentDisposition.ALIGNED for item in dispositions):
        return BurnsAlignmentDisposition.ALIGNED, BurnsAlignmentReason.NONE
    if all(item is BurnsAlignmentDisposition.AMBIGUOUS for item in dispositions):
        reason = reasons[0] if len(set(reasons)) == 1 else BurnsAlignmentReason.MIXED_TARGET_RESULTS
        return BurnsAlignmentDisposition.AMBIGUOUS, reason
    if all(item is BurnsAlignmentDisposition.UNRESOLVED_REFERENCE for item in dispositions):
        reason = reasons[0] if len(set(reasons)) == 1 else BurnsAlignmentReason.MIXED_TARGET_RESULTS
        return BurnsAlignmentDisposition.UNRESOLVED_REFERENCE, reason
    return BurnsAlignmentDisposition.PARTIAL, BurnsAlignmentReason.MIXED_TARGET_RESULTS


def align_burns_annotation(
    annotation: BurnsAnnotation,
    index: ReviewedCucIndex,
) -> BurnsAnnotationAlignment:
    parsed = parse_burns_reference(
        ktu=annotation.ktu,
        reference=annotation.references,
        textual_status=annotation.textual_status,
    )

    if parsed.status is BurnsReferenceStatus.NON_TEXTUAL:
        return BurnsAnnotationAlignment(
            annotation_id=annotation.annotation_id,
            record_ids=annotation.record_ids,
            parsed_reference=parsed,
            disposition=BurnsAlignmentDisposition.NON_TEXTUAL,
            reason=BurnsAlignmentReason.NON_TEXTUAL,
            occurrences=(),
        )

    if parsed.status is not BurnsReferenceStatus.PARSED:
        return BurnsAnnotationAlignment(
            annotation_id=annotation.annotation_id,
            record_ids=annotation.record_ids,
            parsed_reference=parsed,
            disposition=BurnsAlignmentDisposition.UNRESOLVED_REFERENCE,
            reason=BurnsAlignmentReason.REFERENCE_PARSE_FAILED,
            occurrences=(),
        )

    if not parsed.targets:
        raise ValueError("parsed Burns reference produced no targets")

    tablets = {target.tablet for target in parsed.targets}
    if any(tablet not in index.tablet_nodes for tablet in tablets):
        return BurnsAnnotationAlignment(
            annotation_id=annotation.annotation_id,
            record_ids=annotation.record_ids,
            parsed_reference=parsed,
            disposition=BurnsAlignmentDisposition.OUT_OF_CUC,
            reason=BurnsAlignmentReason.TABLET_NOT_IN_CUC,
            occurrences=(),
        )

    occurrences = tuple(
        _resolve_target(annotation, target, ordinal, index)
        for ordinal, target in enumerate(parsed.targets)
    )
    disposition, reason = _summarize_occurrences(occurrences)
    return BurnsAnnotationAlignment(
        annotation_id=annotation.annotation_id,
        record_ids=annotation.record_ids,
        parsed_reference=parsed,
        disposition=disposition,
        reason=reason,
        occurrences=occurrences,
    )


def align_burns_source(
    source: NormalizedBurnsSource,
    index: ReviewedCucIndex,
) -> tuple[BurnsAnnotationAlignment, ...]:
    seen: set[str] = set()
    results: list[BurnsAnnotationAlignment] = []
    for annotation in source.annotations:
        if annotation.annotation_id in seen:
            raise ValueError(f"duplicate Burns annotation id: {annotation.annotation_id}")
        seen.add(annotation.annotation_id)
        results.append(align_burns_annotation(annotation, index))
    return tuple(results)


def _target_payload(target: BurnsTarget) -> dict[str, object]:
    return {
        "tablet": target.tablet,
        "column": target.column,
        "line": target.line,
    }


def _occurrence_payload(occurrence: BurnsAlignmentOccurrence) -> dict[str, object]:
    return {
        "occurrence_id": occurrence.occurrence_id,
        "target_ordinal": occurrence.target_ordinal,
        "target": _target_payload(occurrence.target),
        "disposition": occurrence.disposition.value,
        "reason": occurrence.reason.value,
        "confidence": occurrence.confidence.value,
        "anchor_kind": occurrence.anchor_kind.value if occurrence.anchor_kind else None,
        "anchor_nodes": list(occurrence.anchor_nodes),
        "context_line_node": occurrence.context_line_node,
        "candidate_line_nodes": list(occurrence.candidate_line_nodes),
        "candidate_spans": [list(span) for span in occurrence.candidate_spans],
    }


def _alignment_map(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
) -> dict[str, BurnsAnnotationAlignment]:
    source_ids = [annotation.annotation_id for annotation in source.annotations]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("normalized source contains duplicate annotation ids")

    by_id: dict[str, BurnsAnnotationAlignment] = {}
    for alignment in alignments:
        if alignment.annotation_id in by_id:
            raise ValueError(f"duplicate alignment id: {alignment.annotation_id}")
        by_id[alignment.annotation_id] = alignment

    if set(by_id) != set(source_ids):
        raise ValueError("alignment ids do not exactly cover normalized annotations")
    return by_id


def build_alignment_report(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> dict[str, object]:
    by_alignment = _alignment_map(source, alignments)

    records_by_id = {}
    for record in source.records:
        if record.record_id in records_by_id:
            raise ValueError(f"duplicate normalized source record id: {record.record_id}")
        records_by_id[record.record_id] = record

    entries: list[dict[str, object]] = []
    claimed_record_ids: set[str] = set()
    ordered_annotations = sorted(
        source.annotations,
        key=lambda item: (item.worksheet_id, item.first_source_row, item.annotation_id),
    )
    for annotation in ordered_annotations:
        alignment = by_alignment[annotation.annotation_id]
        expected_alignment = align_burns_annotation(annotation, index)
        if alignment != expected_alignment:
            raise ValueError(
                "alignment does not match deterministic Burns→CUC resolution for "
                f"{annotation.annotation_id}"
            )
        if alignment.record_ids != annotation.record_ids:
            raise ValueError(
                f"alignment record provenance differs for {annotation.annotation_id}"
            )

        source_records: list[dict[str, object]] = []
        for record_id in annotation.record_ids:
            record = records_by_id.get(record_id)
            if record is None:
                raise ValueError(
                    f"annotation {annotation.annotation_id} references missing source record {record_id}"
                )
            if record_id in claimed_record_ids:
                raise ValueError(
                    f"source record is claimed by more than one annotation: {record_id}"
                )
            claimed_record_ids.add(record_id)
            source_records.append(
                {
                    "record_id": record.record_id,
                    "source_file": record.source_file,
                    "source_row": record.source_row,
                    "source_page": record.source_page,
                }
            )

        parsed = alignment.parsed_reference
        entries.append(
            {
                "annotation_id": annotation.annotation_id,
                "record_ids": list(annotation.record_ids),
                "source_records": source_records,
                "original_ktu": parsed.original_ktu,
                "original_reference": parsed.original_reference,
                "parsed_reference": {
                    "status": parsed.status.value,
                    "reason": parsed.reason.value,
                    "targets": [_target_payload(target) for target in parsed.targets],
                },
                "disposition": alignment.disposition.value,
                "reason": alignment.reason.value,
                "occurrences": [
                    _occurrence_payload(occurrence)
                    for occurrence in sorted(
                        alignment.occurrences,
                        key=lambda item: item.target_ordinal,
                    )
                ],
            }
        )

    if claimed_record_ids != set(records_by_id):
        raise ValueError("normalized source records are not exactly partitioned by annotations")

    disposition_counts = dict(
        sorted(Counter(item.disposition.value for item in alignments).items())
    )
    compatibility = index.compatibility
    compatibility_payload: dict[str, object] | None
    if compatibility is None:
        compatibility_payload = None
    else:
        compatibility_payload = {
            "repository": compatibility.repository,
            "commit": compatibility.commit,
            "version": compatibility.version,
            "manifest_sha256": compatibility.manifest_sha256,
        }

    return {
        "schema": "burns-cuc-alignment-report-v1",
        "counts": {
            "records": len(source.records),
            "annotations": len(source.annotations),
            "dispositions": disposition_counts,
        },
        "cuc_compatibility": compatibility_payload,
        "annotations": entries,
    }


def alignment_report_json(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> str:
    return json.dumps(
        build_alignment_report(source, alignments, index),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )