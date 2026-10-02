"""Feature-only Burns Text-Fabric module over the reviewed CUC warp.

The module owns no nodes and no warp. Exact Burns lexical occurrences are
represented on existing CUC word carriers with deterministic per-start lanes;
ordinary edge features link the carrier to subsequent words of multi-word spans.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Protocol

from .alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentDisposition,
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
    build_alignment_report,
)
from .annotations import NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex, reviewed_cuc_compatibility_payload
from .module import _compatibility_payload
from .publication import publish_stage_noreplace
from .tablet_findspots import BurnsTabletFindspots, derive_tablet_findspots

SCHEMA = "burns-feature-module-v3"
REPORT_FILE = "burns-feature-module-report.json"

CATEGORY_NAMES: Mapping[int, str] = MappingProxyType(
    {
        1: "divine_name",
        2: "personal_name",
        3: "geographical_name",
        4: "cultic_jargon",
        5: "cultic_commodity",
        6: "cultic_location",
        7: "cultic_time_event",
        8: "cultic_personnel",
        9: "cultic_action",
    }
)

_LANE_FIELDS = (
    "burns_occurrence_id",
    "burns_annotation_id",
    "burns_headword",
    "burns_root",
    "burns_category",
    "burns_semantic_status",
    "burns_worksheet_role",
    "burns_section",
    "burns_span_length",
)
_FINDSPOT_FIELDS = (
    "burns_locus",
    "burns_room",
    "burns_point",
    "burns_depth",
    "burns_disputed",
)


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


@dataclass(frozen=True)
class BurnsFeatureModule:
    node_features: Mapping[str, Mapping[int, str | int]]
    edge_features: Mapping[str, Mapping[int, frozenset[int]]]
    metadata: Mapping[str, Mapping[str, str]]
    max_lane: int
    occurrence_lanes: Mapping[tuple[int, int], tuple[str, str, tuple[int, ...]]]
    findspot_audit: BurnsTabletFindspots


def _feature_name(base: str, lane: int) -> str:
    return f"{base}_{lane}"


def _feature_metadata(name: str, *, value_type: str, description: str) -> dict[str, str]:
    compatibility = reviewed_cuc_compatibility_payload()
    return {
        "valueType": value_type,
        "module": "Burns",
        "moduleSchema": SCHEMA,
        "cucRepository": str(compatibility["repository"]),
        "cucCommit": str(compatibility["commit"]),
        "cucVersion": str(compatibility["version"]),
        "cucManifestSha256": str(compatibility["manifest_sha256"]),
        "description": description,
    }


def _immutable_nodes(
    values: Mapping[str, Mapping[int, str | int]],
) -> Mapping[str, Mapping[int, str | int]]:
    return MappingProxyType(
        {
            name: MappingProxyType(dict(sorted(feature.items())))
            for name, feature in sorted(values.items())
            if feature
        }
    )


def _immutable_edges(
    values: Mapping[str, Mapping[int, set[int] | frozenset[int]]],
) -> Mapping[str, Mapping[int, frozenset[int]]]:
    return MappingProxyType(
        {
            name: MappingProxyType(
                {
                    node: frozenset(targets)
                    for node, targets in sorted(feature.items())
                    if targets
                }
            )
            for name, feature in sorted(values.items())
            if any(feature.values())
        }
    )


def _immutable_metadata(
    values: Mapping[str, Mapping[str, str]],
) -> Mapping[str, Mapping[str, str]]:
    return MappingProxyType(
        {
            name: MappingProxyType(dict(sorted(metadata.items())))
            for name, metadata in sorted(values.items())
        }
    )


def build_feature_module(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> BurnsFeatureModule:
    """Build a weft-only Burns module on existing CUC word/tablet nodes."""

    _compatibility_payload(index)
    build_alignment_report(source, alignments, index)

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate Burns annotation id")

    grouped: dict[int, list[tuple[tuple[object, ...], object, object, tuple[int, ...]]]] = {}
    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError("alignment references unknown Burns annotation")
        for occurrence in alignment.occurrences:
            if not (
                occurrence.disposition is BurnsAlignmentDisposition.ALIGNED
                and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
                and occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
                and occurrence.anchor_nodes
            ):
                continue

            span = tuple(occurrence.anchor_nodes)
            if len(set(span)) != len(span):
                raise ValueError("exact Burns lexical span contains duplicate CUC words")
            if any(node not in index.word_g_cons for node in span):
                raise ValueError("exact Burns lexical span contains non-word CUC node")
            identity = (
                alignment.annotation_id,
                occurrence.target_ordinal,
                occurrence.occurrence_id,
            )
            grouped.setdefault(span[0], []).append((identity, annotation, occurrence, span))

    node_features: dict[str, dict[int, str | int]] = {}
    edge_features: dict[str, dict[int, set[int]]] = {}
    occurrence_lanes: dict[tuple[int, int], tuple[str, str, tuple[int, ...]]] = {}
    max_lane = 0

    for start, entries in sorted(grouped.items()):
        for lane, (identity, annotation, occurrence, span) in enumerate(
            sorted(entries, key=lambda item: item[0]),
            1,
        ):
            max_lane = max(max_lane, lane)
            try:
                category = CATEGORY_NAMES[annotation.workbook_number]
            except KeyError as exc:
                raise ValueError("unsupported Burns workbook category") from exc

            values: dict[str, str | int] = {
                "burns_occurrence_id": occurrence.occurrence_id,
                "burns_annotation_id": annotation.annotation_id,
                "burns_headword": annotation.headword,
                "burns_category": category,
                "burns_semantic_status": annotation.semantic_status.value,
                "burns_worksheet_role": annotation.worksheet_role.value,
                "burns_section": annotation.section,
                "burns_span_length": len(span),
            }
            if annotation.root:
                values["burns_root"] = annotation.root

            for base, value in values.items():
                node_features.setdefault(_feature_name(base, lane), {})[start] = value

            if len(span) > 1:
                edge_features.setdefault(_feature_name("burns_span", lane), {})[start] = set(span[1:])

            occurrence_lanes[(start, lane)] = (
                annotation.annotation_id,
                occurrence.occurrence_id,
                span,
            )

    findspots = derive_tablet_findspots(source, index)
    for name, values in findspots.node_features.items():
        if values:
            node_features[name] = dict(values)

    immutable_nodes = _immutable_nodes(node_features)
    immutable_edges = _immutable_edges(edge_features)

    metadata: dict[str, dict[str, str]] = {}
    for name in immutable_nodes:
        if name.startswith("burns_span_length_"):
            metadata[name] = _feature_metadata(
                name,
                value_type="int",
                description="Length in CUC words of one exact Burns lexical occurrence lane",
            )
        elif name in _FINDSPOT_FIELDS:
            metadata[name] = _feature_metadata(
                name,
                value_type="str",
                description="Consistent Burns observation on an existing CUC tablet",
            )
        else:
            metadata[name] = _feature_metadata(
                name,
                value_type="str",
                description="Scalar metadata for one exact Burns lexical occurrence lane",
            )
    for name in immutable_edges:
        metadata[name] = _feature_metadata(
            name,
            value_type="int",
            description=(
                "Subsequent CUC word members of one exact Burns lexical occurrence; "
                "the source/carrier word is the implicit first member"
            ),
        )

    return BurnsFeatureModule(
        node_features=immutable_nodes,
        edge_features=immutable_edges,
        metadata=_immutable_metadata(metadata),
        max_lane=max_lane,
        occurrence_lanes=MappingProxyType(dict(sorted(occurrence_lanes.items()))),
        findspot_audit=findspots,
    )


def _plain_module(module: BurnsFeatureModule) -> tuple[dict, dict, dict]:
    return (
        {name: dict(values) for name, values in module.node_features.items()},
        {
            name: {node: frozenset(targets) for node, targets in values.items()}
            for name, values in module.edge_features.items()
        },
        {name: dict(values) for name, values in module.metadata.items()},
    )


def _source_payload(source: NormalizedBurnsSource) -> list[dict[str, object]]:
    return [
        asdict(record)
        for record in sorted(
            source.records,
            key=lambda row: (row.worksheet_id, row.source_row, row.record_id),
        )
    ]


def build_feature_module_report(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
    module: BurnsFeatureModule,
) -> dict[str, object]:
    expected = build_feature_module(source, alignments, index)
    if _plain_module(module) != _plain_module(expected):
        raise ValueError("Burns feature module does not match deterministic source/alignment data")

    feature_files = sorted(
        f"{name}.tf"
        for name in (*module.node_features.keys(), *module.edge_features.keys())
    )
    return {
        "schema": SCHEMA,
        "cuc_compatibility": _compatibility_payload(index),
        "counts": {
            "source_records": len(source.records),
            "annotations": len(source.annotations),
            "exact_lexical_occurrences": len(module.occurrence_lanes),
            "start_words": len({carrier for carrier, _ in module.occurrence_lanes}),
            "max_lane": module.max_lane,
        },
        "feature_inventory": feature_files,
        "occurrence_lanes": [
            {
                "carrier_node": carrier,
                "lane": lane,
                "annotation_id": annotation_id,
                "occurrence_id": occurrence_id,
                "span_nodes": list(span),
            }
            for (carrier, lane), (annotation_id, occurrence_id, span)
            in module.occurrence_lanes.items()
        ],
        "findspot_audit": {
            "conflicts": {
                str(node): {field: list(values) for field, values in fields.items()}
                for node, fields in module.findspot_audit.conflicts.items()
            },
            "incomplete": {
                str(node): list(fields)
                for node, fields in module.findspot_audit.incomplete.items()
            },
            "unmapped_record_ids": list(module.findspot_audit.unmapped_record_ids),
        },
        "source_records": _source_payload(source),
        "alignment": build_alignment_report(source, alignments, index),
    }


def write_feature_module(
    module: BurnsFeatureModule,
    report: Mapping[str, object],
    output_dir: str | Path,
    *,
    fabric_factory: Callable[..., _FabricLike] | None = None,
) -> bool:
    """Publish a complete feature-only Burns module to an absent path."""

    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite an existing Burns feature module: {output}")
    if report.get("schema") != SCHEMA:
        raise ValueError("Burns feature module report has wrong schema")

    expected = frozenset(
        f"{name}.tf"
        for name in (*module.node_features.keys(), *module.edge_features.keys())
    )
    if any(name in expected for name in ("otype.tf", "oslots.tf", "otext.tf")):
        raise ValueError("Burns feature module must not contain warp/config replacement files")
    if sorted(expected) != list(report.get("feature_inventory", [])):
        raise ValueError("Burns feature module report inventory disagrees with module features")

    report_text = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".burns-feature-stage-", dir=output.parent))
    try:
        if fabric_factory is None:
            from tf.fabric import Fabric
            fabric_factory = Fabric
        fabric = fabric_factory(locations=[], modules=[], silent="deep")
        saved = bool(
            fabric.save(
                nodeFeatures={
                    name: dict(values)
                    for name, values in module.node_features.items()
                },
                edgeFeatures={
                    name: {node: set(targets) for node, targets in values.items()}
                    for name, values in module.edge_features.items()
                },
                metaData={
                    name: dict(values)
                    for name, values in module.metadata.items()
                },
                location=str(stage),
                module="",
                silent="deep",
            )
        )
        if not saved:
            return False

        entries = tuple(stage.iterdir())
        staged = {
            path.name
            for path in entries
            if path.is_file() and not path.is_symlink()
        }
        invalid = sorted(
            path.name
            for path in entries
            if path.is_symlink() or not path.is_file()
        )
        if staged != expected or invalid:
            raise RuntimeError(
                "unexpected Burns feature-module stage inventory: "
                f"missing={sorted(expected - staged)}, "
                f"extra={sorted(staged - expected)}, invalid={invalid}"
            )

        (stage / REPORT_FILE).write_text(report_text, encoding="utf-8")
        if output.exists() or output.is_symlink():
            raise ValueError(f"Burns feature-module output appeared during staging: {output}")
        publish_stage_noreplace(stage, output)
        return True
    finally:
        if stage.exists():
            shutil.rmtree(stage)
