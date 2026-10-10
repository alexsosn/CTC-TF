from __future__ import annotations

import argparse
from pathlib import Path

from .alignment import align_burns_source
from .annotations import BurnsNormalizationError, normalize_workbook_records
from .cuc_index import CucCompatibilityError, build_reviewed_cuc_index
from .feature_module import (
    build_feature_module,
    build_feature_module_report,
    write_feature_module,
)
from .module import build_burns_module, build_burns_module_report, write_burns_module
from .pdf_source import load_pdf_directory
from .source import SourceValidationError, load_csv_directory



def _add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path)
    parser.add_argument("--input-format", choices=("csv", "pdf"), required=True)
    parser.add_argument("--output", type=Path, required=True)


def _add_cuc_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cuc",
        type=Path,
        required=True,
        help="exact reviewed CUC 0.2.8 Text-Fabric directory (load before Burns at query time)",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize Burns Workbooks as a CUC-aligned Text-Fabric module"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    module = sub.add_parser(
        "module",
        help="feature-only CUC module (existing nodes only; no warp replacement)",
    )
    _add_source_arguments(module)
    _add_cuc_argument(module)

    module_v1 = sub.add_parser(
        "module-v1",
        help="explicit legacy v1 feature-module format (JSON annotations; compatibility only)",
    )
    _add_source_arguments(module_v1)
    _add_cuc_argument(module_v1)

    return parser


def _load_source(args: argparse.Namespace):
    return (
        load_csv_directory(args.source)
        if args.input_format == "csv"
        else load_pdf_directory(args.source)
    )


def _run_module(args: argparse.Namespace) -> int:
    """Compatibility writer: only reachable through explicit ``module-v1``."""
    try:
        source = _load_source(args)
    except SourceValidationError as exc:
        raise SystemExit(f"source validation failed: {exc}") from exc

    try:
        normalized = normalize_workbook_records(source.records)
    except BurnsNormalizationError as exc:
        raise SystemExit(f"Burns normalization failed: {exc}") from exc

    try:
        index = build_reviewed_cuc_index(args.cuc)
    except CucCompatibilityError as exc:
        raise SystemExit(f"CUC validation failed: {exc}") from exc

    alignments = align_burns_source(normalized, index)
    module = build_burns_module(normalized, alignments, index)
    report = build_burns_module_report(normalized, alignments, index, module)
    try:\n        saved = write_burns_module(module, report, args.output)\n    except ValueError as exc:\n        raise SystemExit(f"legacy publication failed: {exc}") from exc\n    if not saved:
        raise SystemExit("Text-Fabric refused the generated Burns module")

    print(
        f"materialized {len(source.files)} Workbook {args.input_format.upper()} files / "
        f"{len(normalized.records)} records / {len(normalized.annotations)} annotations "
        f"as a legacy v1 CUC-aligned Burns feature module at {args.output}"
    )
    return 0


def _reject_module_overlap(source: Path, cuc: Path, output: Path) -> None:
    """Protect all three trees, including ``..`` and symlinked ancestors."""
    source_root = source.resolve()
    cuc_root = cuc.resolve()
    output_root = output.resolve()
    for root, label in ((source_root, "source"), (cuc_root, "CUC")):
        if output_root == root or output_root.is_relative_to(root) or root.is_relative_to(output_root):
            raise SystemExit(f"native Burns output overlaps {label} directory: {output}")


def _run_feature_module(args: argparse.Namespace) -> int:
    """Publish the corrected feature-only Burns module over reviewed CUC."""

    try:
        source = _load_source(args)
    except SourceValidationError as exc:
        raise SystemExit(f"source validation failed: {exc}") from exc

    _reject_module_overlap(source.root, args.cuc, args.output)
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit(
            f"Burns feature-module output already exists (refusing to overwrite): {args.output}"
        )

    try:
        normalized = normalize_workbook_records(source.records)
    except BurnsNormalizationError as exc:
        raise SystemExit(f"Burns normalization failed: {exc}") from exc
    try:
        index = build_reviewed_cuc_index(args.cuc)
    except CucCompatibilityError as exc:
        raise SystemExit(f"CUC validation failed: {exc}") from exc

    alignments = align_burns_source(normalized, index)
    module = build_feature_module(normalized, alignments, index)
    report = build_feature_module_report(normalized, alignments, index, module)
    try:\n        saved = write_feature_module(module, report, args.output)\n    except ValueError as exc:\n        raise SystemExit(f"module publication failed: {exc}") from exc\n    if not saved:
        raise SystemExit("Text-Fabric refused the Burns feature-only module")

    print(
        f"materialized {len(source.files)} Workbook {args.input_format.upper()} files / "
        f"{len(normalized.records)} records / {len(normalized.annotations)} annotations "
        f"as a feature-only Burns module at {args.output}; "
        f"load ordered Text-Fabric locations [{args.cuc.resolve()}, {args.output.resolve()}]"
    )
    return 0

def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "module":
        return _run_feature_module(args)
    if args.command == "module-v1":
        return _run_module(args)
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
