#!/usr/bin/env python3
"""Audit Burns→CUC alignment locally without exposing source content by default.

The default stdout payload contains aggregate counts only. A full alignment
report, which necessarily contains Burns-derived source provenance and reference
text, is written only when the caller explicitly supplies ``--report``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sources import WORKBOOKS, ensure  # noqa: E402
from ugarit_context_parsing.alignment import (  # noqa: E402
    BurnsAlignmentReason,
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
    _headword_tokens,
    align_burns_source,
    alignment_report_json,
)
from ugarit_context_parsing.annotations import (  # noqa: E402
    NormalizedBurnsSource,
    normalize_workbook_records,
)
from ugarit_context_parsing.cuc_index import ReviewedCucIndex, build_reviewed_cuc_index  # noqa: E402
from ugarit_context_parsing.pdf_source import load_pdf_directory  # noqa: E402


def _counter_payload(counter: Counter[str | int]) -> dict[str, int]:
    return {
        str(key): value
        for key, value in sorted(counter.items(), key=lambda item: str(item[0]))
    }


_SAFE_PUNCTUATION = frozenset(".,;:-/?+()[]")


def _source_safe_shape(value: str) -> str:
    """Mask source text while retaining coarse reference syntax for aggregate audit."""

    text = " ".join((value or "").split())
    parts: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isdigit():
            end = index + 1
            while end < len(text) and text[end].isdigit():
                end += 1
            parts.append("N")
            index = end
            continue
        if char.isalpha():
            end = index + 1
            while end < len(text) and text[end].isalpha():
                end += 1
            run = text[index:end]
            if run and all(item in "IVXLCDM" for item in run):
                parts.append("R")
            elif run and all(item in "ivxlcdm" for item in run):
                parts.append("r")
            else:
                parts.append("A")
            index = end
            continue
        if char.isspace():
            parts.append(" ")
        elif char in _SAFE_PUNCTUATION:
            parts.append(char)
        else:
            parts.append("P")
        index += 1
    return "".join(parts).strip()


def _candidate_count_bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    return "2+"


def aggregate_lexical_gap_stats(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> dict[str, object]:
    """Characterize HEADWORD_NOT_FOUND structurally without source strings."""

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in lexical-gap audit source")

    occurrence_count = 0
    headword_token_counts: Counter[int] = Counter()
    line_word_counts: Counter[int] = Counter()
    overlap_counts: Counter[str] = Counter()
    prefix_candidates: Counter[str] = Counter()
    suffix_candidates: Counter[str] = Counter()
    contains_candidates: Counter[str] = Counter()

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError("alignment references unknown annotation in lexical-gap audit")
        for occurrence in alignment.occurrences:
            if occurrence.reason is not BurnsAlignmentReason.HEADWORD_NOT_FOUND:
                continue
            line_node = occurrence.context_line_node
            if line_node is None or line_node not in index.line_words:
                raise ValueError("HEADWORD_NOT_FOUND occurrence lacks indexed context line")
            words = index.line_words[line_node]
            try:
                values = tuple(index.word_g_cons[word] for word in words)
            except KeyError as exc:
                raise ValueError("lexical-gap audit line references word without g_cons") from exc

            tokens = _headword_tokens(annotation.headword)
            occurrence_count += 1
            headword_token_counts[len(tokens)] += 1
            line_word_counts[len(values)] += 1

            wanted = Counter(tokens)
            available = Counter(values)
            exact_hits = sum(min(count, available[token]) for token, count in wanted.items())
            if exact_hits == 0:
                overlap_counts["none"] += 1
            elif exact_hits == sum(wanted.values()):
                overlap_counts["all_present_noncontiguous_or_reordered"] += 1
            else:
                overlap_counts["partial"] += 1

            if len(tokens) == 1:
                token = tokens[0]
                prefix = sum(value != token and value.startswith(token) for value in values)
                suffix = sum(value != token and value.endswith(token) for value in values)
                contains = sum(value != token and token in value for value in values)
                prefix_candidates[_candidate_count_bucket(prefix)] += 1
                suffix_candidates[_candidate_count_bucket(suffix)] += 1
                contains_candidates[_candidate_count_bucket(contains)] += 1

    return {
        "occurrences": occurrence_count,
        "headword_token_counts": _counter_payload(headword_token_counts),
        "line_word_counts": _counter_payload(line_word_counts),
        "exact_token_overlap": _counter_payload(overlap_counts),
        "single_token_prefix_candidates": _counter_payload(prefix_candidates),
        "single_token_suffix_candidates": _counter_payload(suffix_candidates),
        "single_token_contains_candidates": _counter_payload(contains_candidates),
    }


def aggregate_alignment_stats(
    *,
    file_count: int,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
) -> dict[str, object]:
    """Return source-safe aggregate statistics from completed alignments."""

    annotation_dispositions: Counter[str] = Counter()
    reference_statuses: Counter[str] = Counter()
    reference_failure_reasons: Counter[str] = Counter()
    reference_failure_shapes: Counter[str] = Counter()
    occurrence_dispositions: Counter[str] = Counter()
    occurrence_reasons: Counter[str] = Counter()
    anchor_kinds: Counter[str] = Counter()
    word_span_lengths: Counter[int] = Counter()
    node_annotations: dict[int, set[str]] = defaultdict(set)

    for alignment in alignments:
        annotation_dispositions[alignment.disposition.value] += 1
        reference_statuses[alignment.parsed_reference.status.value] += 1
        if alignment.reason is BurnsAlignmentReason.REFERENCE_PARSE_FAILED:
            reason = alignment.parsed_reference.reason.value
            reference_failure_reasons[reason] += 1
            reference_failure_shapes[
                f"{reason}|ktu={_source_safe_shape(alignment.parsed_reference.original_ktu)}"
                f"|ref={_source_safe_shape(alignment.parsed_reference.original_reference)}"
            ] += 1
        for occurrence in alignment.occurrences:
            occurrence_dispositions[occurrence.disposition.value] += 1
            occurrence_reasons[occurrence.reason.value] += 1
            if occurrence.anchor_kind is not None:
                anchor_kinds[occurrence.anchor_kind.value] += 1
            if occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN:
                word_span_lengths[len(occurrence.anchor_nodes)] += 1
            for node in occurrence.anchor_nodes:
                node_annotations[node].add(alignment.annotation_id)

    annotation_multiplicities = tuple(len(ids) for ids in node_annotations.values())
    return {
        "source": {
            "files": file_count,
            "records": len(source.records),
            "annotations": len(source.annotations),
        },
        "annotation_dispositions": _counter_payload(annotation_dispositions),
        "reference_statuses": _counter_payload(reference_statuses),
        "reference_failure_reasons": _counter_payload(reference_failure_reasons),
        "reference_failure_shapes": _counter_payload(reference_failure_shapes),
        "occurrence_dispositions": _counter_payload(occurrence_dispositions),
        "occurrence_reasons": _counter_payload(occurrence_reasons),
        "anchor_kinds": _counter_payload(anchor_kinds),
        "word_span_lengths": _counter_payload(word_span_lengths),
        "selected_anchor_node_multiplicity": {
            "nodes_with_multiple_annotations": sum(
                1 for count in annotation_multiplicities if count > 1
            ),
            "max_annotations_per_node": max(annotation_multiplicities, default=0),
        },
    }


def _write_private_report(path: Path, payload: str) -> None:
    """Atomically publish an explicitly requested local report as owner-only."""

    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            staged = handle.name
            os.chmod(staged, 0o600)
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
        staged = None
        os.chmod(path, 0o600)
    finally:
        if staged is not None:
            try:
                os.unlink(staged)
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Burns→CUC alignment; stdout is aggregate-only by default."
    )
    parser.add_argument(
        "--cuc",
        required=True,
        type=Path,
        help="path to the reviewed CUC 0.2.8 Text-Fabric directory",
    )
    parser.add_argument(
        "--workbooks",
        type=Path,
        help="local Workbooks directory; omit to fetch/verify the pinned deposit",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="explicit local path for the full Burns-derived alignment report",
    )
    args = parser.parse_args(argv)

    workbooks_path = (
        args.workbooks.expanduser()
        if args.workbooks is not None
        else ensure(WORKBOOKS, root=ROOT)
    )
    workbook_source = load_pdf_directory(workbooks_path)
    normalized = normalize_workbook_records(workbook_source.records)
    index = build_reviewed_cuc_index(args.cuc.expanduser())
    alignments = align_burns_source(normalized, index)

    stats = aggregate_alignment_stats(
        file_count=len(workbook_source.files),
        source=normalized,
        alignments=alignments,
    )
    print(
        json.dumps(
            stats,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    if args.report is not None:
        _write_private_report(
            args.report,
            alignment_report_json(normalized, alignments, index),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
