#!/usr/bin/env python3
"""Audit the actual pinned Burns Workbooks against reviewed CUC; log counts only.

Never commit, upload, or print copyrighted source rows, lexical labels or
locators. The runner downloads the original Workbooks and discards derivatives.
"""
from __future__ import annotations

import argparse
import json
import resource
from collections import Counter
from pathlib import Path

from tf.fabric import Fabric

from scripts.audit_burns_alignment import (
    aggregate_alignment_stats,
    aggregate_feature_only_lane_stats,
    aggregate_headword_expression_stats,
    aggregate_lexical_gap_stats,
    aggregate_line_address_drift_stats,
)
from ugarit_context_parsing.alignment import (
    BurnsAlignmentConfidence, BurnsAlignmentDisposition, BurnsAnchorKind,
    align_burns_source,
)
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cli import main as materialize
from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index
from ugarit_context_parsing.feature_module import CATEGORY_NAMES, REPORT_FILE, SCHEMA
from ugarit_context_parsing.source import load_csv_directory


def audit(source_root: Path, cuc_root: Path, output: Path) -> None:
    source = load_csv_directory(source_root)
    normalized = normalize_workbook_records(source.records)
    category_counts = Counter(item.workbook_number for item in normalized.annotations)
    if len(source.files) != 45 or set(category_counts) != set(CATEGORY_NAMES):
        raise AssertionError(
            f"unexpected real source inventory: files={len(source.files)}, "
            f"workbook_numbers={sorted(category_counts)}"
        )
    index = build_reviewed_cuc_index(cuc_root)
    alignments = align_burns_source(normalized, index)
    alignment_stats = aggregate_alignment_stats(
        file_count=len(source.files),
        source=normalized,
        alignments=alignments,
    )
    lexical_gap_stats = aggregate_lexical_gap_stats(
        source=normalized,
        alignments=alignments,
        index=index,
    )
    headword_expression_stats = aggregate_headword_expression_stats(
        source=normalized,
        alignments=alignments,
    )
    line_address_drift_stats = aggregate_line_address_drift_stats(
        source=normalized,
        alignments=alignments,
        index=index,
    )
    feature_only_lane_stats = aggregate_feature_only_lane_stats(
        source=normalized,
        alignments=alignments,
        index=index,
    )
    disposition_counts = Counter(item.disposition.value for item in alignments)
    annotation_reasons = Counter((item.disposition.value, item.reason.value) for item in alignments)
    occurrence_reasons = Counter(
        (item.disposition.value, item.reason.value)
        for alignment in alignments for item in alignment.occurrences
    )
    category_dispositions = Counter(
        (CATEGORY_NAMES[annotation.workbook_number], alignment.disposition.value)
        for annotation, alignment in zip(normalized.annotations, alignments, strict=True)
    )
    occurrence_counts = Counter(
        (item.disposition.value, item.confidence.value, item.anchor_kind.value if item.anchor_kind else "none")
        for alignment in alignments for item in alignment.occurrences
    )
    selected = sum(
        item.disposition is BurnsAlignmentDisposition.ALIGNED
        and item.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
        and item.anchor_kind is BurnsAnchorKind.WORD_SPAN
        for alignment in alignments for item in alignment.occurrences
    )
    expected_headword_outcomes = {
        "ambiguous_span": sum(
            item.reason.value == "ambiguous_headword_span"
            for alignment in alignments for item in alignment.occurrences
        ),
        "matched": selected,
        "not_found": sum(
            item.reason.value == "headword_not_found"
            for alignment in alignments for item in alignment.occurrences
        ),
    }
    if int(feature_only_lane_stats["occurrences"]) != selected:
        raise AssertionError(
            "feature-only lane audit diverges from exact lexical occurrence count: "
            f"actual={feature_only_lane_stats['occurrences']!r} expected={selected!r}"
        )
    if int(line_address_drift_stats["occurrences"]) != expected_headword_outcomes["not_found"]:
        raise AssertionError(
            "line-address drift denominator diverges from HEADWORD_NOT_FOUND occurrences: "
            f"actual={line_address_drift_stats['occurrences']!r} "
            f"expected={expected_headword_outcomes['not_found']!r}"
        )
    if headword_expression_stats["outcomes"] != {
        key: value for key, value in expected_headword_outcomes.items() if value
    }:
        raise AssertionError(
            "headword-expression denominator diverges from alignment outcomes: "
            f"actual={headword_expression_stats['outcomes']!r} "
            f"expected={expected_headword_outcomes!r}"
        )
    eligible = int(headword_expression_stats["eligible_occurrences"])
    for partition_name in ("exclusive_classes", "syntax_signatures"):
        partition = headword_expression_stats[partition_name]
        if sum(int(bucket["occurrences"]) for bucket in partition.values()) != eligible:
            raise AssertionError(
                f"headword-expression {partition_name} does not partition eligible occurrences"
            )
    if materialize([
        "module", str(source_root), "--input-format", "csv", "--cuc", str(cuc_root),
        "--output", str(output),
    ]) != 0:
        raise AssertionError("default native module command failed on actual Burns source")
    report = json.loads((output / REPORT_FILE).read_text(encoding="utf-8"))
    if report["schema"] != SCHEMA:
        raise AssertionError("real Burns output has wrong feature-only schema")
    counts = report["counts"]
    if (
        counts["source_records"] != len(source.records)
        or counts["annotations"] != len(normalized.annotations)
        or counts["exact_lexical_occurrences"] != selected
        or counts["max_lane"] != feature_only_lane_stats["max_lane"]
    ):
        raise AssertionError(
            "real Burns local report lost records, annotations, lexical occurrences, or lanes: "
            f"actual={counts!r}"
        )
    inventory = {item.name for item in output.iterdir()}
    if inventory != set(report["feature_inventory"]) | {REPORT_FILE}:
        raise AssertionError("real Burns output/report feature inventories disagree")
    forbidden = {
        "otype.tf", "oslots.tf", "otext.tf",
        "burns_annotations.tf", "burns_annotation_ids.tf", "burns_headwords.tf",
        "burns_semantic_statuses.tf", "burns_worksheet_roles.tf", "burns_sections.tf",
    }
    leaked = sorted(forbidden & inventory)
    if leaked:
        raise AssertionError(f"forbidden warp/legacy Burns features leaked: {leaked!r}")

    original = Fabric(locations=[str(cuc_root.resolve())], modules=[""], silent="deep").loadAll(silent="deep")
    combined = Fabric(
        locations=[str(cuc_root.resolve()), str(output.resolve())],
        modules=[""], silent="deep",
    ).loadAll(silent="deep")
    if original is None or combined is None:
        raise AssertionError("real Burns feature-only module cannot be composed with reviewed CUC")
    if (
        combined.F.otype.maxSlot != original.F.otype.maxSlot
        or combined.F.otype.maxNode != original.F.otype.maxNode
    ):
        raise AssertionError("Burns feature-only module changed the CUC node universe")
    for node in range(1, original.F.otype.maxNode + 1):
        if combined.F.otype.v(node) != original.F.otype.v(node):
            raise AssertionError(f"CUC original node type changed at node {node}")
        if node > original.F.otype.maxSlot and (
            tuple(combined.E.oslots.s(node)) != tuple(original.E.oslots.s(node))
        ):
            raise AssertionError(f"CUC original sign extent changed at node {node}")
    if tuple(combined.F.otype.s("entity")):
        raise AssertionError("feature-only Burns module created entity nodes")

    if len(report["occurrence_lanes"]) != selected:
        raise AssertionError("feature-only report lost exact lexical occurrences")
    for item in report["occurrence_lanes"]:
        carrier = int(item["carrier_node"])
        lane = int(item["lane"])
        span = tuple(int(node) for node in item["span_nodes"])
        if not span or span[0] != carrier:
            raise AssertionError("feature-only report has invalid carrier/span identity")
        if combined.F.otype.v(carrier) != "word":
            raise AssertionError("Burns lexical lane carrier is not a CUC word")
        occurrence_feature = combined.Fs(f"burns_occurrence_id_{lane}", warn=False)
        length_feature = combined.Fs(f"burns_span_length_{lane}", warn=False)
        if not occurrence_feature or occurrence_feature.v(carrier) != item["occurrence_id"]:
            raise AssertionError("Burns occurrence lane is not natively queryable")
        if not length_feature or length_feature.v(carrier) != len(span):
            raise AssertionError("Burns span length disagrees with local report")
        edge = combined.Es(f"burns_span_{lane}", warn=False)
        actual_tail = tuple(edge.f(carrier)) if edge else ()
        if actual_tail != span[1:]:
            raise AssertionError("Burns span edge disagrees with local report")

    lexical_prefixes = (
        "burns_occurrence_id_", "burns_annotation_id_", "burns_headword_",
        "burns_root_", "burns_category_", "burns_semantic_status_",
        "burns_worksheet_role_", "burns_section_", "burns_span_length_",
    )
    for name in combined.Fall():
        if name.startswith(lexical_prefixes):
            feature = combined.Fs(name, warn=False)
            for node in feature.data:
                if combined.F.otype.v(node) != "word":
                    raise AssertionError(f"lexical lane feature {name} leaked beyond CUC words")
    for name in ("burns_locus", "burns_room", "burns_point", "burns_depth", "burns_disputed"):
        if name in combined.Fall():
            for node in combined.Fs(name).data:
                if combined.F.otype.v(node) != "tablet":
                    raise AssertionError(f"real Burns findspot {name} leaked beyond tablet")
    if report["counts"]["annotations"] != sum(disposition_counts.values()):
        raise AssertionError("real Burns alignments did not account for all annotations")
    # Aggregate diagnosis distinguishes a CUC coverage boundary from a lexical
    # alignment failure; no source-derived strings or identifying locators.
    summary = {
        "workbook_files": len(source.files),
        "source_records": len(source.records),
        "source_annotations": len(normalized.annotations),
        "annotation_categories": {CATEGORY_NAMES[i]: category_counts[i] for i in sorted(category_counts)},
        "alignment_dispositions": dict(sorted(disposition_counts.items())),
        "reference_statuses": alignment_stats["reference_statuses"],
        "reference_failure_reasons": alignment_stats["reference_failure_reasons"],
        "reference_failure_shapes": alignment_stats["reference_failure_shapes"],
        "annotation_reasons": {"/".join(key): value for key, value in sorted(annotation_reasons.items())},
        "occurrence_reasons": {"/".join(key): value for key, value in sorted(occurrence_reasons.items())},
        "category_dispositions": {"/".join(key): value for key, value in sorted(category_dispositions.items())},
        "occurrence_states": {"/".join(key): count for key, count in sorted(occurrence_counts.items())},
        "exact_lexical_occurrences": selected,
        "lexical_gap": lexical_gap_stats,
        "feature_only_lanes": feature_only_lane_stats,
        "headword_expression": headword_expression_stats,
        "line_address_drift": line_address_drift_stats,
        "tablet_findspot_conflicts": len(report["findspot_audit"]["conflicts"]),
        "tablet_findspot_incomplete": len(report["findspot_audit"]["incomplete"]),
        "unmapped_findspot_records": len(report["findspot_audit"]["unmapped_record_ids"]),
        "native_output_bytes": sum(item.stat().st_size for item in output.iterdir()),
        "peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    print("real_burns_audit=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
    print("Real Burns Workbooks parser + reviewed CUC feature-only module + lossless inventory: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("cuc_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.source_root, args.cuc_root, args.output)


if __name__ == "__main__":
    main()
