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
    align_burns_source,
    alignment_report_json,
)
from ugarit_context_parsing.annotations import (  # noqa: E402
    NormalizedBurnsSource,
    normalize_workbook_records,
)
from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index  # noqa: E402
from ugarit_context_parsing.pdf_source import load_pdf_directory  # noqa: E402


def _counter_payload(counter: Counter[str | int]) -> dict[str, int]:
    return {
        str(key): value
        for key, value in sorted(counter.items(), key=lambda item: str(item[0]))
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
    occurrence_dispositions: Counter[str] = Counter()
    occurrence_reasons: Counter[str] = Counter()
    anchor_kinds: Counter[str] = Counter()
    word_span_lengths: Counter[int] = Counter()
    node_annotations: dict[int, set[str]] = defaultdict(set)

    for alignment in alignments:
        annotation_dispositions[alignment.disposition.value] += 1
        reference_statuses[alignment.parsed_reference.status.value] += 1
        if alignment.reason is BurnsAlignmentReason.REFERENCE_PARSE_FAILED:
            reference_failure_reasons[alignment.parsed_reference.reason.value] += 1
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
