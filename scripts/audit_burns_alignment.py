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
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sources import WORKBOOKS, ensure  # noqa: E402
from ugarit_context_parsing.alignment import (  # noqa: E402
    BurnsAlignmentConfidence,
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



_EDITORIAL_MARKERS = "*†!?"
_HEADWORD_AUDIT_OUTCOMES = ("ambiguous_span", "matched", "not_found")


def _delimiter_balance(value: str, opener: str, closer: str) -> tuple[bool, int, int]:
    """Return (unbalanced, opener_count, max_depth) for one delimiter pair."""

    depth = 0
    max_depth = 0
    openers = 0
    unbalanced = False
    for char in value:
        if char == opener:
            openers += 1
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == closer:
            if depth == 0:
                unbalanced = True
            else:
                depth -= 1
    if depth:
        unbalanced = True
    return unbalanced, openers, max_depth


def _parenthesis_shape(value: str) -> str:
    has_parenthesis = "(" in value or ")" in value
    if not has_parenthesis:
        return "none"

    unbalanced, openers, max_depth = _delimiter_balance(value, "(", ")")
    if unbalanced:
        return "unbalanced"
    if openers > 1 or max_depth > 1:
        return "multiple_or_nested"

    text = value.strip()
    start = text.find("(")
    end = text.rfind(")")
    if start == 0 and end == len(text) - 1:
        return "whole_expression"
    if start == 0:
        return "leading"
    if end == len(text) - 1:
        return "trailing"
    return "medial"


def _trailing_editorial_markers(value: str) -> str:
    """Return the distinct documented trailing markers in canonical order."""

    seen: set[str] = set()
    for raw in value.split():
        token = raw
        while token and token[-1] in _EDITORIAL_MARKERS:
            seen.add(token[-1])
            token = token[:-1]
    return "".join(marker for marker in _EDITORIAL_MARKERS if marker in seen)


def classify_headword_expression(headword: str) -> dict[str, object]:
    """Classify authored headword punctuation without interpreting its semantics."""

    text = unicodedata.normalize("NFC", headword or "")
    parentheses = "(" in text or ")" in text
    square_brackets = "[" in text or "]" in text
    slash = "/" in text
    trailing_editorial_markers = _trailing_editorial_markers(text)
    trailing_editorial_marker = bool(trailing_editorial_markers)
    unbalanced_parentheses, _, _ = _delimiter_balance(text, "(", ")")
    unbalanced_square_brackets, _, _ = _delimiter_balance(text, "[", "]")

    if parentheses:
        exclusive_class = "parentheses"
    elif square_brackets:
        exclusive_class = "square_brackets"
    elif slash:
        exclusive_class = "slash"
    elif trailing_editorial_marker:
        exclusive_class = "marker_only"
    else:
        exclusive_class = "clean"

    return {
        "parentheses": parentheses,
        "square_brackets": square_brackets,
        "slash": slash,
        "trailing_editorial_marker": trailing_editorial_marker,
        "trailing_editorial_markers": trailing_editorial_markers,
        "unbalanced_parentheses": unbalanced_parentheses,
        "unbalanced_square_brackets": unbalanced_square_brackets,
        "parenthesis_shape": _parenthesis_shape(text),
        "exclusive_class": exclusive_class,
    }


def _headword_audit_outcome(occurrence) -> str | None:
    """Return a lexical-expression outcome only for an exactly resolved line context."""

    if occurrence.context_line_node is None:
        return None
    if (
        occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
        and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
        and occurrence.reason is BurnsAlignmentReason.NONE
    ):
        return "matched"
    if (
        occurrence.anchor_kind is BurnsAnchorKind.LINE
        and occurrence.reason is BurnsAlignmentReason.HEADWORD_NOT_FOUND
    ):
        return "not_found"
    if (
        occurrence.anchor_kind is BurnsAnchorKind.LINE
        and occurrence.reason is BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN
    ):
        return "ambiguous_span"
    return None


def _headword_audit_bucket(counter: Counter[str]) -> dict[str, int]:
    return {
        **{name: counter.get(name, 0) for name in _HEADWORD_AUDIT_OUTCOMES},
        "occurrences": sum(counter.values()),
    }


def aggregate_headword_expression_stats(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
) -> dict[str, object]:
    """Cross-tab authored headword shapes against current exact lexical outcomes.

    The payload contains only static shape labels and counts. It intentionally
    omits Burns strings, locators, ids, source provenance, and CUC line content.
    """

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in headword-expression audit source")

    outcomes: Counter[str] = Counter()
    flag_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    exclusive_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    parenthesis_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    syntax_signature_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    marker_signature_buckets: dict[str, Counter[str]] = defaultdict(Counter)

    boolean_flags = (
        "parentheses",
        "square_brackets",
        "slash",
        "trailing_editorial_marker",
        "unbalanced_parentheses",
        "unbalanced_square_brackets",
    )

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError(
                "alignment references unknown annotation in headword-expression audit"
            )
        shape = classify_headword_expression(annotation.headword)
        for occurrence in alignment.occurrences:
            outcome = _headword_audit_outcome(occurrence)
            if outcome is None:
                continue
            outcomes[outcome] += 1
            exclusive_buckets[str(shape["exclusive_class"])][outcome] += 1

            signature_parts = [
                label
                for flag, label in (
                    ("parentheses", "parentheses"),
                    ("square_brackets", "square_brackets"),
                    ("slash", "slash"),
                    ("trailing_editorial_marker", "marker"),
                )
                if bool(shape[flag])
            ]
            syntax_signature = "+".join(signature_parts) if signature_parts else "clean"
            syntax_signature_buckets[syntax_signature][outcome] += 1

            marker_signature = str(shape["trailing_editorial_markers"])
            if marker_signature:
                marker_signature_buckets[marker_signature][outcome] += 1

            for flag in boolean_flags:
                if bool(shape[flag]):
                    flag_buckets[flag][outcome] += 1
            parenthesis_shape = str(shape["parenthesis_shape"])
            if parenthesis_shape != "none":
                parenthesis_buckets[parenthesis_shape][outcome] += 1

    return {
        "eligible_occurrences": sum(outcomes.values()),
        "outcomes": _counter_payload(outcomes),
        "exclusive_classes": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(exclusive_buckets.items())
        },
        "flags": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(flag_buckets.items())
        },
        "parenthesis_shapes": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(parenthesis_buckets.items())
        },
        "syntax_signatures": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(syntax_signature_buckets.items())
        },
        "editorial_marker_signatures": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(marker_signature_buckets.items())
        },
    }


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
