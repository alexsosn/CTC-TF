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

from ugarit_context_parsing.alignment import (
    BurnsAlignmentConfidence, BurnsAlignmentDisposition, BurnsAnchorKind,
    align_burns_source,
)
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cli import main as materialize
from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index
from ugarit_context_parsing.entity_extension import CATEGORY_NAMES
from ugarit_context_parsing.entity_writer import REPORT_FILE, SCHEMA
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
    if materialize([
        "module", str(source_root), "--input-format", "csv", "--cuc", str(cuc_root),
        "--output", str(output),
    ]) != 0:
        raise AssertionError("default native module command failed on actual Burns source")
    report = json.loads((output / REPORT_FILE).read_text(encoding="utf-8"))
    if report["schema"] != SCHEMA:
        raise AssertionError("real Burns output has wrong schema")
    if report["counts"] != {
        "source_records": len(source.records),
        "annotations": len(normalized.annotations),
        "native_entities": selected,
    }:
        raise AssertionError("real Burns local report lost records, annotations, or lexical occurrences")
    inventory = {item.name for item in output.iterdir()}
    if inventory != set(report["feature_inventory"]) | {REPORT_FILE}:
        raise AssertionError("real Burns output/report feature inventories disagree")
    if "burns_annotations.tf" in inventory:
        raise AssertionError("legacy per-word JSON feature leaked into real native output")

    original = Fabric(locations=[str(cuc_root.resolve())], modules=[""], silent="deep").loadAll(silent="deep")
    combined = Fabric(
        locations=[str(cuc_root.resolve()), str(output.resolve())],
        modules=[""], silent="deep",
    ).loadAll(silent="deep")
    if original is None or combined is None:
        raise AssertionError("real Burns native module cannot be composed with reviewed CUC")
    if combined.F.otype.maxSlot != original.F.otype.maxSlot:
        raise AssertionError("CUC sign-slot boundary changed")
    if combined.F.otype.maxNode != original.F.otype.maxNode + selected:
        raise AssertionError("real Burns extended warp has wrong total node count")
    for node in range(1, original.F.otype.maxNode + 1):
        if combined.F.otype.v(node) != original.F.otype.v(node):
            raise AssertionError(f"CUC original node type changed at node {node}")
        if node > original.F.otype.maxSlot and (
            set(combined.E.oslots.s(node)) != set(original.E.oslots.s(node))
        ):
            raise AssertionError(f"CUC original sign extent changed at node {node}")
    entity_nodes = tuple(combined.F.otype.s("entity"))
    if len(entity_nodes) != selected:
        raise AssertionError("real Burns entity count differs from exact lexical alignment inventory")
    for node in entity_nodes:
        if not combined.F.burns_headword.v(node) or not combined.E.oslots.s(node):
            raise AssertionError("real Burns entity missing source headword or sign extent")
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
        "annotation_reasons": {"/".join(key): value for key, value in sorted(annotation_reasons.items())},
        "occurrence_reasons": {"/".join(key): value for key, value in sorted(occurrence_reasons.items())},
        "category_dispositions": {"/".join(key): value for key, value in sorted(category_dispositions.items())},
        "occurrence_states": {"/".join(key): count for key, count in sorted(occurrence_counts.items())},
        "native_entities": selected,
        "tablet_findspot_conflicts": len(report["findspot_audit"]["conflicts"]),
        "tablet_findspot_incomplete": len(report["findspot_audit"]["incomplete"]),
        "unmapped_findspot_records": len(report["findspot_audit"]["unmapped_record_ids"]),
        "native_output_bytes": sum(item.stat().st_size for item in output.iterdir()),
        "peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    print("real_burns_audit=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
    print("Real Burns Workbooks parser + reviewed CUC native module + lossless inventory: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("cuc_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.source_root, args.cuc_root, args.output)


if __name__ == "__main__":
    main()
