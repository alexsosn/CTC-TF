"""One-shot, non-overwriting publisher for the experimental native entity warp.

This does not replace the v1 `module` CLI or silently migrate old output.
It publishes to a NEW directory only; schema migration and source audits are
separate gates for issue #68. The output is Burns-derived local data.
"""
from __future__ import annotations

import json
import shutil
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
    """Publish a complete entity overlay only to an absent output directory.

    Reject even an empty pre-existing output, rather than adopting or deleting
    potentially foreign datasets. Staging is a sibling, so publication is one
    directory rename after TF inventory and report have been validated.
    """
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite an existing Burns entity output: {output}")
    # Enforce the exact CUC fingerprint before allocating an extended warp.
    _compatibility_payload(index)
    extension = build_entity_extension(source, alignments, index, api)
    expected = frozenset(
        f"{name}.tf"
        for name in (*extension.node_features, *extension.edge_features)
    )
    if not {"otype.tf", "oslots.tf"}.issubset(expected):
        raise ValueError("Burns entity extension has no complete Text-Fabric warp")
    report = _make_report(source, alignments, index, extension, expected)
    # No path or timestamps are serialized. Source-derived details remain in
    # this local sidecar, not as per-word or per-entity TF features.
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
        if output.exists() or output.is_symlink():
            raise ValueError(f"Burns entity output appeared during staging: {output}")
        stage.replace(output)
        return True
    finally:
        if stage.exists():
            shutil.rmtree(stage)
