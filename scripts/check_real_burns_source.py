#!/usr/bin/env python3
"""Audit the actual pinned Burns Workbooks against reviewed CUC; log counts only.

Never commit, upload, or print copyrighted source rows, lexical labels or
locators. The runner downloads the original Workbooks and discards derivatives.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
from collections import Counter
from pathlib import Path

from tf.fabric import Fabric

from scripts.audit_burns_alignment import (
    aggregate_alignment_stats,
    aggregate_bracket_restoration_research,
    aggregate_complex_headword_expression_research,
    aggregate_feature_only_lane_stats,
    aggregate_headword_candidate_research,
    aggregate_headword_expression_stats,
    aggregate_lexical_gap_stats,
    aggregate_line_address_drift_stats,
    aggregate_residual_clean_gap_research,
    aggregate_token_boundary_research,
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_editorial_research(cuc_root: Path):
    """Load extra CUC editorial features for research on the pinned CI checkout.

    Production alignment must not depend on these files until #79 extends the
    reviewed-CUC fingerprint contract.
    """

    names = ("sign.tf", "emen.tf", "cert.tf", "alt.tf")
    fingerprints = {
        name: {
            "size": (cuc_root / name).stat().st_size,
            "sha256": _sha256(cuc_root / name),
        }
        for name in names
    }
    api = Fabric(locations=[str(cuc_root.resolve())], modules=[""], silent="deep").load(
        "sign emen cert alt",
        silent="deep",
    )
    if not api:
        raise AssertionError("could not load reviewed CUC editorial features for research")

    sign_nodes = tuple(int(node) for node in api.F.otype.s("sign"))
    sign_values = {
        node: str(value)
        for node in sign_nodes
        if (value := api.F.sign.v(node)) is not None
    }
    sign_emen = {
        node: str(value)
        for node in sign_nodes
        if (value := api.F.emen.v(node)) is not None
    }
    sign_cert = {
        node: str(value)
        for node in sign_nodes
        if (value := api.F.cert.v(node)) is not None
    }
    sign_alt = {
        node: str(value)
        for node in sign_nodes
        if (value := api.F.alt.v(node)) is not None
    }
    return sign_values, sign_emen, sign_cert, sign_alt, fingerprints


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
    (
        sign_values,
        sign_emen,
        sign_cert,
        sign_alt,
        editorial_fingerprints,
    ) = _load_editorial_research(cuc_root)
    bracket_restoration_research = aggregate_bracket_restoration_research(
        source=normalized,
        alignments=alignments,
        index=index,
        sign_values=sign_values,
        sign_emen=sign_emen,
        sign_cert=sign_cert,
        sign_alt=sign_alt,
    )
    complex_headword_expression_research = (
        aggregate_complex_headword_expression_research(
            source=normalized,
            alignments=alignments,
            index=index,
        )
    )
    unsupported_brackets = int(
        bracket_restoration_research["lexical_outcomes"].get("unsupported", 0)
    )
    if int(complex_headword_expression_research["occurrences"]) != unsupported_brackets:
        raise AssertionError(
            "complex-expression research denominator diverges from #79 unsupported "
            f"bracket occurrences: actual={complex_headword_expression_research['occurrences']!r} "
            f"expected={unsupported_brackets!r}"
        )
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
    headword_candidate_research = aggregate_headword_candidate_research(
        source=normalized,
        alignments=alignments,
        index=index,
    )
    line_address_drift_stats = aggregate_line_address_drift_stats(
        source=normalized,
        alignments=alignments,
        index=index,
    )
    residual_clean_gap_research = aggregate_residual_clean_gap_research(
        source=normalized,
        alignments=alignments,
        index=index,
    )
    token_boundary_research = aggregate_token_boundary_research(
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
    expected_clean_marker_gaps = sum(
        int(headword_expression_stats["exclusive_classes"].get(name, {}).get("not_found", 0))
        for name in ("clean", "marker_only")
    )
    if int(residual_clean_gap_research["occurrences"]) != expected_clean_marker_gaps:
        raise AssertionError(
            "residual clean-gap denominator diverges from clean/marker HEADWORD_NOT_FOUND: "
            f"actual={residual_clean_gap_research['occurrences']!r} "
            f"expected={expected_clean_marker_gaps!r}"
        )
    if sum(int(value) for value in residual_clean_gap_research["classes"].values()) != expected_clean_marker_gaps:
        raise AssertionError("residual clean-gap classes do not partition denominator")

    expected_boundary_occurrences = sum(
        int(value)
        for key, value in residual_clean_gap_research["token_boundary_span_cardinality"].items()
        if key != "0"
    )
    if int(token_boundary_research["occurrences"]) != expected_boundary_occurrences:
        raise AssertionError(
            "token-boundary research diverges from #81 exact-boundary probe: "
            f"actual={token_boundary_research['occurrences']!r} "
            f"expected={expected_boundary_occurrences!r}"
        )
    if int(token_boundary_research["eligible_clean_marker_gaps"]) != expected_clean_marker_gaps:
        raise AssertionError("token-boundary research clean/marker denominator drifted")

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

    exact_match_rules = {
        occurrence.occurrence_id: occurrence.match_rule
        for alignment in alignments
        for occurrence in alignment.occurrences
        if occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
        and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
    }
    if set(exact_match_rules) != {
        item["occurrence_id"] for item in report["occurrence_lanes"]
    }:
        raise AssertionError("feature-only report and exact alignment occurrence ids diverge")

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
        match_rule_feature = combined.Fs(f"burns_match_rule_{lane}", warn=False)
        length_feature = combined.Fs(f"burns_span_length_{lane}", warn=False)
        if not occurrence_feature or occurrence_feature.v(carrier) != item["occurrence_id"]:
            raise AssertionError("Burns occurrence lane is not natively queryable")
        expected_rule = exact_match_rules[item["occurrence_id"]]
        if not expected_rule or not match_rule_feature or match_rule_feature.v(carrier) != expected_rule:
            raise AssertionError("Burns lexical match-rule provenance diverges from alignment")
        if not length_feature or length_feature.v(carrier) != len(span):
            raise AssertionError("Burns span length disagrees with local report")
        edge = combined.Es(f"burns_span_{lane}", warn=False)
        actual_tail = tuple(edge.f(carrier)) if edge else ()
        if actual_tail != span[1:]:
            raise AssertionError("Burns span edge disagrees with local report")

    lexical_prefixes = (
        "burns_occurrence_id_", "burns_annotation_id_", "burns_headword_",
        "burns_match_rule_", "burns_root_", "burns_category_", "burns_semantic_status_",
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
        "headword_candidate_research": headword_candidate_research,
        "bracket_restoration_research": bracket_restoration_research,
        "complex_headword_expression_research": complex_headword_expression_research,
        "editorial_file_fingerprints": editorial_fingerprints,
        "line_address_drift": line_address_drift_stats,
        "residual_clean_gap_research": residual_clean_gap_research,
        "token_boundary_research": token_boundary_research,
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
