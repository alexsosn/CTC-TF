#!/usr/bin/env python3
"""Audit Appendix→reviewed-CUC tablet concordance using aggregate counts only.

This script deliberately does not create fragment identities or Text-Fabric
features. The Appendix contains KTU/RS/findspot observations, while reviewed
CUC 0.2.8 has no fragment node or RS-number feature. Raw Appendix values remain
local to the runner; stdout contains counts only.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path

from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index
from ugarit_context_parsing.identifiers import normalize_cuc_tablet
from ugarit_context_parsing.source import load_csv_directory
from ugarit_context_parsing.tablet_findspots import classify_findspot_values

_APPENDIX_COLUMNS = (
    "page",
    "ktu",
    "is_subrow",
    "rs_number",
    "genre",
    "locus",
    "room",
    "point",
    "depth",
    "disputed",
    "teo_i_p",
    "sau_p",
    "comments",
)
_FINDSPOT_FIELDS = ("locus", "room", "point", "depth", "disputed")


def aggregate_appendix_concordance(
    *,
    rows: Iterable[Mapping[str, str]],
    cuc_tablets: Collection[str],
) -> dict[str, object]:
    """Return source-safe Appendix/CUC concordance counts.

    A valid KTU identifier uses the same exact normalizer as Burns→CUC
    alignment. Findspot conflict/incompleteness semantics mirror the v2
    Workbooks tablet policy, but this audit does not publish those values.
    """

    source_rows = 0
    valid_ktu_rows = 0
    invalid_ktu_rows = 0
    by_tablet: dict[str, list[Mapping[str, str]]] = {}

    for row in rows:
        source_rows += 1
        tablet = normalize_cuc_tablet(row.get("ktu", ""))
        if not tablet:
            invalid_ktu_rows += 1
            continue
        valid_ktu_rows += 1
        by_tablet.setdefault(tablet, []).append(row)

    valid_tablets = set(by_tablet)
    reviewed = set(cuc_tablets)
    mapped_tablets = valid_tablets & reviewed

    multi_row_tablets = sum(1 for group in by_tablet.values() if len(group) > 1)
    multi_rs_tablets = 0
    mapped_multi_rs_tablets = 0
    for tablet, group in by_tablet.items():
        rs_numbers = {
            row.get("rs_number", "").strip()
            for row in group
            if row.get("rs_number", "").strip()
        }
        if len(rs_numbers) > 1:
            multi_rs_tablets += 1
            if tablet in mapped_tablets:
                mapped_multi_rs_tablets += 1

    conflicts_by_field: Counter[str] = Counter()
    incomplete_by_field: Counter[str] = Counter()
    conflict_tablets: set[str] = set()
    incomplete_tablets: set[str] = set()

    for tablet in mapped_tablets:
        group = by_tablet[tablet]
        for field in _FINDSPOT_FIELDS:
            state, _, _ = classify_findspot_values(
                [row.get(field, "") for row in group]
            )
            if state == "conflict":
                conflicts_by_field[field] += 1
                conflict_tablets.add(tablet)
            elif state == "incomplete":
                incomplete_by_field[field] += 1
                incomplete_tablets.add(tablet)

    mapped_multi_rs = {
        tablet
        for tablet in mapped_tablets
        if len({row.get("rs_number", "").strip() for row in by_tablet[tablet] if row.get("rs_number", "").strip()}) > 1
    }

    return {
        "source_rows": source_rows,
        "valid_ktu_rows": valid_ktu_rows,
        "invalid_ktu_rows": invalid_ktu_rows,
        "unique_valid_tablets": len(valid_tablets),
        "tablets_in_cuc": len(mapped_tablets),
        "tablets_out_of_cuc": len(valid_tablets - reviewed),
        "multi_row_tablets": multi_row_tablets,
        "multi_rs_tablets": multi_rs_tablets,
        "mapped_multi_rs_tablets": mapped_multi_rs_tablets,
        "mapped_multi_rs_tablets_with_findspot_conflict": len(mapped_multi_rs & conflict_tablets),
        "mapped_multi_rs_tablets_with_findspot_incomplete": len(mapped_multi_rs & incomplete_tablets),
        "mapped_tablets_with_findspot_conflict": len(conflict_tablets),
        "mapped_tablets_with_findspot_incomplete": len(incomplete_tablets),
        "findspot_conflicts_by_field": dict(sorted(conflicts_by_field.items())),
        "findspot_incomplete_by_field": dict(sorted(incomplete_by_field.items())),
    }



def aggregate_cross_source_findspots(
    *,
    appendix_rows: Iterable[Mapping[str, str]],
    workbook_rows: Iterable[Mapping[str, str]],
    cuc_tablets: Collection[str],
) -> dict[str, object]:
    """Classify aggregate safety of Workbooks-published tablet values only.

    A Workbooks field is publishable only when all mapped rows for that tablet
    carry one identical nonempty value, matching the production policy.
    Appendix values are never returned.
    """

    reviewed = set(cuc_tablets)
    appendix_by_tablet: dict[str, list[Mapping[str, str]]] = {}
    workbook_by_tablet: dict[str, list[Mapping[str, str]]] = {}
    for row in appendix_rows:
        tablet = normalize_cuc_tablet(row.get("ktu", ""))
        if tablet and tablet in reviewed:
            appendix_by_tablet.setdefault(tablet, []).append(row)
    for row in workbook_rows:
        tablet = normalize_cuc_tablet(row.get("ktu", ""))
        if tablet and tablet in reviewed:
            workbook_by_tablet.setdefault(tablet, []).append(row)

    totals: Counter[str] = Counter()
    by_field: dict[str, Counter[str]] = {field: Counter() for field in _FINDSPOT_FIELDS}
    for tablet, rows in workbook_by_tablet.items():
        appendix_group = appendix_by_tablet.get(tablet, ())
        for field in _FINDSPOT_FIELDS:
            workbook_state, workbook_value, _ = classify_findspot_values(
                [row.get(field, "") for row in rows]
            )
            if workbook_state != "complete" or workbook_value is None:
                continue
            totals["workbook_published_field_values"] += 1
            appendix_state, appendix_value, _ = classify_findspot_values(
                [row.get(field, "") for row in appendix_group]
            )
            if appendix_state == "complete":
                outcome = "agreement" if appendix_value == workbook_value else "complete_disagreement"
            else:
                outcome = f"appendix_{appendix_state}"
            totals[outcome] += 1
            by_field[field][outcome] += 1

    outcomes = (
        "agreement",
        "complete_disagreement",
        "appendix_conflict",
        "appendix_incomplete",
        "appendix_absent",
    )
    result: dict[str, object] = {"workbook_published_field_values": totals["workbook_published_field_values"]}
    for outcome in outcomes:
        result[outcome] = totals[outcome]
    for outcome in outcomes:
        result[f"{outcome}_by_field"] = {
            field: by_field[field][outcome]
            for field in _FINDSPOT_FIELDS
            if by_field[field][outcome]
        }
    return result

def _read_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != _APPENDIX_COLUMNS:
            raise ValueError("Appendix CSV header does not match the reviewed parser schema")
        return tuple(dict(row) for row in reader)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Appendix KTU/RS/findspot concordance against reviewed CUC."
    )
    parser.add_argument("appendix_csv", type=Path)
    parser.add_argument("cuc", type=Path)
    parser.add_argument("--workbooks", type=Path)
    args = parser.parse_args(argv)

    rows = _read_rows(args.appendix_csv.expanduser())
    index = build_reviewed_cuc_index(args.cuc.expanduser())
    stats = aggregate_appendix_concordance(
        rows=rows,
        cuc_tablets=frozenset(index.tablet_nodes),
    )
    print(
        "appendix_cuc_audit="
        + json.dumps(stats, sort_keys=True, separators=(",", ":"))
    )
    if args.workbooks is not None:
        workbook_source = load_csv_directory(args.workbooks.expanduser())
        workbook_rows = tuple(
            {
                "ktu": record.ktu,
                "locus": record.locus,
                "room": record.room,
                "point": record.point,
                "depth": record.depth,
                "disputed": record.disputed,
            }
            for record in workbook_source.records
        )
        cross_source = aggregate_cross_source_findspots(
            appendix_rows=rows,
            workbook_rows=workbook_rows,
            cuc_tablets=frozenset(index.tablet_nodes),
        )
        print(
            "appendix_workbook_findspot_audit="
            + json.dumps(cross_source, sort_keys=True, separators=(",", ":"))
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
