"""Adapter for Agora's already-created, private, empty materializer output.

The public `ugarit-context-parsing module` keeps its strong absent-destination
no-overwrite guarantee. Agora deliberately supplies an existing empty staging
directory and handles final transactional promotion and provenance itself.
This adapter only bridges those two contracts; it never fetches Burns sources
or alters the existing CUC Text-Fabric warp.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil

from .cli import _reject_module_overlap, main as native_main


REPORT_FILE = "burns-feature-module-report.json"
NATIVE_CHILD = ".burns-agora-native-artifact"
WARP_FILES = frozenset({"otype.tf", "oslots.tf", "otext.tf"})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish Burns features into an existing empty Agora sandbox staging directory"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--input-format", required=True, choices=("csv", "pdf"))
    parser.add_argument("--cuc", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output = args.output

    # Do not let a direct caller mistake this internal adapter for the normal
    # native producer: it requires Agora's already-created, empty output root.
    if output.is_symlink() or not output.is_dir():
        raise ValueError(
            "Agora Burns output must be an existing, real, empty staging directory"
        )
    if any(output.iterdir()):
        raise ValueError("Agora Burns staging output is not empty; refusing to overwrite")
    _reject_module_overlap(args.source, args.cuc, output)

    native_target = output / NATIVE_CHILD
    # The native feature-module writer independently requires an absent path,
    # stages to its sibling under output/, and publishes via no-replace. This
    # subdirectory is inside Agora's sole writable output sandbox mount.
    published: list[Path] = []
    try:
        result = native_main([
            "module", str(args.source), "--input-format", args.input_format,
            "--cuc", str(args.cuc), "--output", str(native_target),
        ])
        if result != 0:
            raise RuntimeError(f"native Burns module converter returned {result!r}")
        if native_target.is_symlink() or not native_target.is_dir():
            raise ValueError("native Burns producer did not create a real artifact directory")

        items = tuple(native_target.iterdir())
        names = {entry.name for entry in items}
        if REPORT_FILE not in names or not any(name.endswith(".tf") for name in names):
            raise ValueError("native Burns module is missing its report or TF feature files")
        if names & WARP_FILES:
            raise ValueError("native Burns module attempted to replace CUC warp files")
        for entry in items:
            if entry.is_symlink() or not entry.is_file():
                raise ValueError(f"unexpected non-file/symlink in Burns module: {entry.name}")
            if entry.name != REPORT_FILE and not entry.name.endswith(".tf"):
                raise ValueError(f"unexpected non-feature Burns module output: {entry.name}")

        # File-wise no-replace publication within the *already precreated*
        # Agora staging root. Hard links create destinations atomically and
        # fail if a foreign file appeared; the host owns atomic final publish.
        for entry in items:
            target = output / entry.name
            os.link(entry, target, follow_symlinks=False)
            published.append(target)
        return 0
    except BaseException:
        for target in published:
            target.unlink(missing_ok=True)
        raise
    finally:
        if native_target.is_dir() and not native_target.is_symlink():
            shutil.rmtree(native_target)


if __name__ == "__main__":
    raise SystemExit(main())
