"""Lossless, one-shot publisher for native Burns entity nodes.

The public ``module`` command produces v2 into a NEW output directory.
Legacy v1 remains the explicitly named ``module-v1`` compatibility command.
Generated Burns data is local and must not be redistributed without permission.
"""
from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Protocol

from .alignment import BurnsAnnotationAlignment, build_alignment_report
from .annotations import NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex
from .entity_extension import build_entity_extension
from .module import _compatibility_payload

REPORT_FILE = "burns-entity-report.json"
SCHEMA = "burns-entity-module-v2"


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


def _publish_stage_noreplace(stage: Path, output: Path) -> None:
    """Atomically publish a directory without *ever* replacing a destination.

    POSIX ``Path.replace`` can replace an empty directory created between a
    preceding existence check and the rename. Use the platform's exclusive
    rename primitive. Unsupported kernels/filesystems fail closed; never fall
    back to a race-prone check-then-rename. Stage and output are siblings.
    """
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise OSError(errno.ENOTSUP, "atomic no-replace renameat2 unavailable")
        # AT_FDCWD=-100; RENAME_NOREPLACE=1.
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        outcome = rename(-100, os.fsencode(stage), -100, os.fsencode(output), 1)
    elif sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renamex_np", None)
        if rename is None:
            raise OSError(errno.ENOTSUP, "atomic exclusive renamex_np unavailable")
        # Darwin RENAME_EXCL=0x00000004, not Linux's RENAME_NOREPLACE=1.
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        outcome = rename(os.fsencode(stage), os.fsencode(output), 0x00000004)
    elif os.name == "nt":
        # Unlike POSIX rename, Windows os.rename refuses an existing target.
        os.rename(stage, output)
        return
    else:
        raise OSError(errno.ENOTSUP, "atomic no-replace directory rename unsupported")
    if outcome != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(error, "refusing to overwrite existing Burns entity output", str(output))
        raise OSError(error, os.strerror(error), str(output))


def _source_payload(source: NormalizedBurnsSource) -> list[dict[str, object]]:
    return [
        asdict(record)
        for record in sorted(
            source.records, key=lambda row: (row.worksheet_id, row.source_row, row.record_id)
        )
    ]


def _make_report(source, alignments, index, extension, expected_files):
    return {
        "schema": SCHEMA,
        "cuc_compatibility": _compatibility_payload(index),
        "counts": {
            "source_records": len(source.records),
            "annotations": len(source.annotations),
            "native_entities": len(extension.occurrence_nodes),
        },
        "feature_inventory": sorted(expected_files),
        "entity_occurrences": [
            {"node": node, "annotation_id": annotation, "occurrence_id": occurrence}
            for node, (annotation, occurrence) in extension.occurrence_nodes.items()
        ],
        "findspot_audit": {
            "conflicts": {
                str(node): {field: list(values) for field, values in fields.items()}
                for node, fields in extension.findspot_audit.conflicts.items()
            },
            "incomplete": {
                str(node): list(fields)
                for node, fields in extension.findspot_audit.incomplete.items()
            },
            "unmapped_record_ids": list(extension.findspot_audit.unmapped_record_ids),
        },
        "source_records": _source_payload(source),
        "alignment": build_alignment_report(source, alignments, index),
    }


def write_entity_artifact(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
    api,
    output_dir: str | Path,
    *,
    fabric_factory: Callable[..., _FabricLike] | None = None,
) -> bool:
    """Publish complete TF warp + report to an absent directory only.

    Neither an existing v1 module nor an empty foreign directory is adopted.
    The stage lives beside output for one exclusive, atomic publication after
    validating the generated TF inventory and complete local audit report.
    """
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite an existing Burns entity output: {output}")
    _compatibility_payload(index)
    extension = build_entity_extension(source, alignments, index, api)
    expected = frozenset(
        f"{name}.tf"
        for name in (*extension.node_features, *extension.edge_features)
    )
    if not {"otype.tf", "oslots.tf"}.issubset(expected):
        raise ValueError("Burns entity extension has no complete Text-Fabric warp")
    report = _make_report(source, alignments, index, extension, expected)
    report_text = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".burns-entities-stage-", dir=output.parent))
    try:
        if fabric_factory is None:
            from tf.fabric import Fabric
            fabric_factory = Fabric
        fabric = fabric_factory(locations=[], modules=[], silent="deep")
        saved = bool(fabric.save(
            nodeFeatures={name: dict(values) for name, values in extension.node_features.items()},
            edgeFeatures={name: dict(values) for name, values in extension.edge_features.items()},
            metaData={name: dict(values) for name, values in extension.metadata.items()},
            location=str(stage), module="", silent="deep",
        ))
        if not saved:
            return False
        entries = tuple(stage.iterdir())
        staged = {path.name for path in entries if path.is_file() and not path.is_symlink()}
        invalid = sorted(path.name for path in entries if path.is_symlink() or not path.is_file())
        if staged != expected or invalid:
            raise RuntimeError(
                f"unexpected Burns entity stage inventory: missing={sorted(expected - staged)}, "
                f"extra={sorted(staged - expected)}, invalid={invalid}"
            )
        (stage / REPORT_FILE).write_text(report_text, encoding="utf-8")
        # This check improves diagnostics; the exclusive syscall itself is the
        # authority if another process creates output immediately afterwards.
        if output.exists() or output.is_symlink():
            raise ValueError(f"Burns entity output appeared during staging: {output}")
        _publish_stage_noreplace(stage, output)
        return True
    finally:
        if stage.exists():
            shutil.rmtree(stage)
