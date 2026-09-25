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
            observed = tuple(row.get(field, "").strip() for row in group)
            nonempty = {value for value in observed if value}
            if len(nonempty) > 1:
                conflicts_by_field[field] += 1
                conflict_tablets.add(tablet)
            elif len(nonempty) == 1 and not all(observed):
                incomplete_by_field[field] += 1
                incomplete_tablets.add(tablet)

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
        "mapped_tablets_with_findspot_conflict": len(conflict_tablets),
        "mapped_tablets_with_findspot_incomplete": len(incomplete_tablets),
        "findspot_conflicts_by_field": dict(sorted(conflicts_by_field.items())),
        "findspot_incomplete_by_field": dict(sorted(incomplete_by_field.items())),
    }


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
