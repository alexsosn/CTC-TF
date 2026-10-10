from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Callable, Mapping, Protocol

from .alignment import (
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
    build_alignment_report,
)
from .annotations import BurnsAnnotation, BurnsSourceRecord, NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex, reviewed_cuc_compatibility_payload

MODULE_SCHEMA = "burns-tf-module-v1"
NODE_ANNOTATION_SCHEMA = "burns-node-annotation-v1"
MODULE_REPORT_SCHEMA = "burns-tf-module-report-v1"
REPORT_FILE = "burns-module-report.json"

FEATURES = (
    "burns_annotations",
    "burns_annotation_ids",
    "burns_semantic_statuses",
    "burns_worksheet_roles",
    "burns_sections",
    "burns_headwords",
)
_EXPECTED_TF_FILES = frozenset(f"{feature}.tf" for feature in FEATURES)

_DESCRIPTIONS = {
    "burns_annotations": (
        "Authoritative canonical JSON array of Burns annotation occurrences "
        "aligned to this existing CUC node"
    ),
    "burns_annotation_ids": "Canonical JSON array of Burns semantic annotation IDs",
    "burns_semantic_statuses": "Canonical JSON array of Burns semantic statuses",
    "burns_worksheet_roles": "Canonical JSON array of Burns worksheet roles",
    "burns_sections": "Canonical JSON array of Burns section labels",
    "burns_headwords": "Canonical JSON array of Burns source headwords",
}

_PROJECTION_FIELDS = {
    "burns_annotation_ids": "annotation_id",
    "burns_semantic_statuses": "semantic_status",
    "burns_worksheet_roles": "worksheet_role",
    "burns_sections": "section",
    "burns_headwords": "headword",
}

_ANNOTATION_RECORD_FIELDS = (
    "worksheet_id",
    "workbook_number",
    "workbook_label",
    "worksheet_number",
    "worksheet_role",
    "section",
    "root",
    "headword",
    "ktu",
    "references",
    "textual_status",
    "semantic_status",
    "interpretive_status",
)

_ALIGNMENT_OCCURRENCE_FIELDS = (
    "occurrence_id",
    "target_ordinal",
    "target",
    "disposition",
    "reason",
    "confidence",
    "anchor_kind",
    "anchor_nodes",
    "context_line_node",
    "candidate_line_nodes",
    "candidate_spans",
)


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


@dataclass(frozen=True)
class BurnsModuleData:
    node_features: Mapping[str, Mapping[int, str]]
    metadata: Mapping[str, Mapping[str, str]]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _reviewed_compatibility_identity() -> dict[str, str]:
    payload = reviewed_cuc_compatibility_payload()
    return {
        "repository": str(payload["repository"]),
        "commit": str(payload["commit"]),
        "version": str(payload["version"]),
        "manifest_sha256": str(payload["manifest_sha256"]),
    }


def _compatibility_payload(index: ReviewedCucIndex) -> dict[str, object]:
    compatibility = index.compatibility
    if compatibility is None:
        raise ValueError("Burns TF module requires a reviewed CUC compatibility identity")

    expected = _reviewed_compatibility_identity()
    actual = {
        "repository": compatibility.repository,
        "commit": compatibility.commit,
        "version": compatibility.version,
        "manifest_sha256": compatibility.manifest_sha256,
    }
    if actual != expected:
        raise ValueError(
            "Burns TF module requires the exact reviewed CUC identity: "
            f"expected {expected!r}; got {actual!r}"
        )
    return reviewed_cuc_compatibility_payload()


def _record_payload(record: BurnsSourceRecord) -> dict[str, object]:
    return {
        "record_id": record.record_id,
        "source_file": record.source_file,
        "source_row": record.source_row,
        "source_page": record.source_page,
        "section": record.section,
        "root": record.root,
        "headword": record.headword,
        "ktu": record.ktu,
        "references": record.references,
        "locus": record.locus,
        "room": record.room,
        "point": record.point,
        "depth": record.depth,
        "disputed": record.disputed,
        "comments": record.comments,
        "worksheet_id": record.worksheet_id,
        "workbook_number": record.workbook_number,
        "workbook_label": record.workbook_label,
        "worksheet_number": record.worksheet_number,
        "worksheet_role": record.worksheet_role.value,
        "textual_status": record.textual_status.value,
        "semantic_status": record.semantic_status.value,
        "interpretive_status": record.interpretive_status.value,
    }


def _target_payload(target) -> dict[str, object]:
    return {
        "tablet": target.tablet,
        "column": target.column,
        "line": target.line,
    }


def _occurrence_payload(
    annotation: BurnsAnnotation,
    alignment: BurnsAnnotationAlignment,
    records_by_id: Mapping[str, BurnsSourceRecord],
    occurrence,
) -> dict[str, object]:
    source_records = []
    for record_id in annotation.record_ids:
        record = records_by_id.get(record_id)
        if record is None:
            raise ValueError(
                f"annotation {annotation.annotation_id} references missing source record {record_id}"
            )
        source_records.append(_record_payload(record))

    return {
        "schema": NODE_ANNOTATION_SCHEMA,
        "annotation_id": annotation.annotation_id,
        "occurrence_id": occurrence.occurrence_id,
        "target_ordinal": occurrence.target_ordinal,
        "record_ids": list(annotation.record_ids),
        "source_records": source_records,
        "worksheet_id": annotation.worksheet_id,
        "workbook_number": annotation.workbook_number,
        "workbook_label": annotation.workbook_label,
        "worksheet_number": annotation.worksheet_number,
        "worksheet_role": annotation.worksheet_role.value,
        "section": annotation.section,
        "root": annotation.root,
        "headword": annotation.headword,
        "ktu": annotation.ktu,
        "references": annotation.references,
        "textual_status": annotation.textual_status.value,
        "semantic_status": annotation.semantic_status.value,
        "interpretive_status": annotation.interpretive_status.value,
        "annotation_disposition": alignment.disposition.value,
        "annotation_reason": alignment.reason.value,
        "disposition": occurrence.disposition.value,
        "reason": occurrence.reason.value,
        "confidence": occurrence.confidence.value,
        "anchor_kind": occurrence.anchor_kind.value if occurrence.anchor_kind else None,
        "anchor_nodes": list(occurrence.anchor_nodes),
        "context_line_node": occurrence.context_line_node,
        "target": _target_payload(occurrence.target),
        "candidate_line_nodes": list(occurrence.candidate_line_nodes),
        "candidate_spans": [list(span) for span in occurrence.candidate_spans],
    }


def _payload_identity(payload: Mapping[str, object]) -> tuple[object, ...]:
    anchor_nodes = payload.get("anchor_nodes")
    if not isinstance(anchor_nodes, list) or not all(type(node) is int for node in anchor_nodes):
        raise ValueError("Burns node annotation has invalid anchor_nodes")
    return (
        payload.get("annotation_id"),
        payload.get("occurrence_id"),
        payload.get("anchor_kind"),
        tuple(anchor_nodes),
    )


def burns_node_annotations(value: str) -> tuple[dict[str, object], ...]:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("burns_annotations must contain valid JSON") from exc
    if not isinstance(payload, list):
        raise ValueError("burns_annotations must be a JSON array")

    result: list[dict[str, object]] = []
    previous_identity: tuple[object, ...] | None = None
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("burns_annotations array members must be objects")
        if item.get("schema") != NODE_ANNOTATION_SCHEMA:
            raise ValueError("unsupported Burns node annotation schema")
        identity = _payload_identity(item)
        if previous_identity is not None and identity <= previous_identity:
            raise ValueError("burns_annotations entries are not in strict canonical identity order")
        previous_identity = identity
        result.append(dict(item))

    if _canonical_json(result) != value:
        raise ValueError("burns_annotations value is not canonical JSON")
    return tuple(result)


def _project_payloads(
    payloads: tuple[dict[str, object], ...],
) -> dict[str, str]:
    return {
        feature: _canonical_json(
            sorted({str(item[payload_field]) for item in payloads})
        )
        for feature, payload_field in _PROJECTION_FIELDS.items()
    }


def _expected_feature_metadata(feature: str) -> dict[str, str]:
    compatibility = reviewed_cuc_compatibility_payload()
    required_features = compatibility["required_features"]
    node_type_counts = compatibility["node_type_counts"]
    section_types = compatibility["section_types"]
    section_features = compatibility["section_features"]
    assert isinstance(required_features, list)
    assert isinstance(node_type_counts, dict)
    assert isinstance(section_types, list)
    assert isinstance(section_features, list)
    return {
        "valueType": "str",
        "module": "Burns",
        "moduleSchema": MODULE_SCHEMA,
        "cucRepository": str(compatibility["repository"]),
        "cucCommit": str(compatibility["commit"]),
        "cucVersion": str(compatibility["version"]),
        "cucManifestSha256": str(compatibility["manifest_sha256"]),
        "cucCompatibilitySchema": str(compatibility["schema"]),
        "cucRequiredFeatures": ",".join(str(value) for value in required_features),
        "cucNodeTypeCounts": _canonical_json(node_type_counts),
        "cucSectionTypes": ",".join(str(value) for value in section_types),
        "cucSectionFeatures": ",".join(str(value) for value in section_features),
        "description": _DESCRIPTIONS[feature],
    }


def _immutable_nested(
    values: Mapping[str, Mapping[int, str]],
) -> Mapping[str, Mapping[int, str]]:
    return MappingProxyType(
        {
            feature: MappingProxyType(dict(sorted(node_values.items())))
            for feature, node_values in sorted(values.items())
        }
    )


def _immutable_metadata(
    values: Mapping[str, Mapping[str, str]],
) -> Mapping[str, Mapping[str, str]]:
    return MappingProxyType(
        {
            feature: MappingProxyType(dict(sorted(metadata.items())))
            for feature, metadata in sorted(values.items())
        }
    )


def build_burns_module(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> BurnsModuleData:
    _compatibility_payload(index)

    # Reuse #26 as the integrity gate. This rejects missing/extra/forged
    # alignments and proves every normalized source record is partitioned
    # exactly once before any node payload is emitted.
    build_alignment_report(source, alignments, index)

    alignments_by_id = {alignment.annotation_id: alignment for alignment in alignments}
    records_by_id = {record.record_id: record for record in source.records}

    per_node: dict[int, dict[tuple[object, ...], tuple[str, dict[str, object]]]] = {}
    ordered_annotations = sorted(
        source.annotations,
        key=lambda item: (item.worksheet_id, item.first_source_row, item.annotation_id),
    )
    for annotation in ordered_annotations:
        alignment = alignments_by_id[annotation.annotation_id]
        for occurrence in sorted(alignment.occurrences, key=lambda item: item.target_ordinal):
            if occurrence.anchor_kind is None or not occurrence.anchor_nodes:
                continue
            if occurrence.anchor_kind is not BurnsAnchorKind.WORD_SPAN and len(occurrence.anchor_nodes) != 1:
                raise ValueError("non-span Burns occurrence must select exactly one CUC node")

            payload = _occurrence_payload(annotation, alignment, records_by_id, occurrence)
            identity = _payload_identity(payload)
            canonical = _canonical_json(payload)
            for node in occurrence.anchor_nodes:
                entries = per_node.setdefault(node, {})
                previous = entries.get(identity)
                if previous is not None:
                    if previous[0] != canonical:
                        raise ValueError(
                            "conflicting Burns payloads share one stable occurrence identity"
                        )
                    continue
                entries[identity] = (canonical, payload)

    authoritative: dict[int, str] = {}
    projections: dict[str, dict[int, str]] = {
        feature: {} for feature in FEATURES if feature != "burns_annotations"
    }
    for node in sorted(per_node):
        payloads = [
            item[1]
            for _, item in sorted(per_node[node].items(), key=lambda pair: pair[0])
        ]
        value = _canonical_json(payloads)
        authoritative[node] = value

        # Derive every convenience feature from the authoritative serialized
        # value, keeping burns_annotations as the sole source of truth.
        parsed = burns_node_annotations(value)
        for feature, projected_value in _project_payloads(parsed).items():
            projections[feature][node] = projected_value

    node_features: dict[str, Mapping[int, str]] = {
        "burns_annotations": authoritative,
        **projections,
    }
    metadata = {
        feature: _expected_feature_metadata(feature)
        for feature in FEATURES
    }
    return BurnsModuleData(
        node_features=_immutable_nested(node_features),
        metadata=_immutable_metadata(metadata),
    )


def _plain_module(module: BurnsModuleData) -> tuple[dict[str, dict[int, str]], dict[str, dict[str, str]]]:
    node_features = {
        feature: dict(values) for feature, values in module.node_features.items()
    }
    metadata = {
        feature: dict(values) for feature, values in module.metadata.items()
    }
    return node_features, metadata


def build_burns_module_report(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
    module: BurnsModuleData,
) -> dict[str, object]:
    expected = build_burns_module(source, alignments, index)
    if _plain_module(module) != _plain_module(expected):
        raise ValueError("Burns TF module does not match deterministic source/alignment data")

    alignment_report = build_alignment_report(source, alignments, index)
    compatibility = _compatibility_payload(index)
    disposition_counts = dict(
        sorted(Counter(alignment.disposition.value for alignment in alignments).items())
    )
    selected_occurrences = [
        occurrence
        for alignment in alignments
        for occurrence in alignment.occurrences
        if occurrence.anchor_kind is not None and occurrence.anchor_nodes
    ]
    anchor_kind_counts = dict(
        sorted(Counter(occurrence.anchor_kind.value for occurrence in selected_occurrences).items())
    )
    source_records = [
        _record_payload(record)
        for record in sorted(
            source.records,
            key=lambda item: (item.worksheet_id, item.source_row, item.record_id),
        )
    ]
    return {
        "schema": MODULE_REPORT_SCHEMA,
        "cuc_compatibility": compatibility,
        "counts": {
            "records": len(source.records),
            "annotations": len(source.annotations),
            "alignment_dispositions": disposition_counts,
            "selected_occurrences": len(selected_occurrences),
            "anchor_kinds": anchor_kind_counts,
            "touched_nodes": len(module.node_features["burns_annotations"]),
        },
        "feature_inventory": sorted(FEATURES),
        "source_records": source_records,
        "alignment": alignment_report,
    }


def _make_fabric(factory: Callable[..., _FabricLike] | None) -> _FabricLike:
    if factory is None:
        try:
            from tf.fabric import Fabric
        except ImportError as exc:
            raise RuntimeError("Text-Fabric is required to write Burns module features") from exc
        factory = Fabric
    return factory(locations=[], modules=[], silent="deep")


def _validate_authoritative_placement(
    parsed_by_node: Mapping[int, tuple[dict[str, object], ...]],
) -> dict[tuple[str, str], tuple[str, tuple[int, ...], str, set[int]]]:
    occurrences: dict[tuple[str, str], tuple[str, tuple[int, ...], str, set[int]]] = {}
    for node, payloads in parsed_by_node.items():
        if type(node) is not int or node <= 0:
            raise ValueError("Burns authoritative placement uses a non-positive node id")
        for payload in payloads:
            annotation_id = payload.get("annotation_id")
            occurrence_id = payload.get("occurrence_id")
            if not isinstance(annotation_id, str) or not annotation_id:
                raise ValueError("Burns node payload has invalid annotation identity")
            if not isinstance(occurrence_id, str) or not occurrence_id:
                raise ValueError("Burns node payload has invalid occurrence identity")

            anchor_kind = payload.get("anchor_kind")
            if anchor_kind not in {"tablet", "line", "word_span"}:
                raise ValueError("Burns node payload has invalid anchor kind")
            raw_anchor_nodes = payload.get("anchor_nodes")
            if not isinstance(raw_anchor_nodes, list) or not raw_anchor_nodes:
                raise ValueError("Burns node payload has empty or invalid anchor placement")
            if not all(type(anchor) is int and anchor > 0 for anchor in raw_anchor_nodes):
                raise ValueError("Burns node payload has invalid anchor placement")
            anchor_nodes = tuple(raw_anchor_nodes)
            if len(set(anchor_nodes)) != len(anchor_nodes):
                raise ValueError("Burns node payload has duplicate anchor placement")
            if anchor_kind in {"tablet", "line"} and len(anchor_nodes) != 1:
                raise ValueError("Burns structural anchor must have exactly one node")
            if node not in anchor_nodes:
                raise ValueError("Burns payload placement is outside its declared anchor nodes")

            key = (annotation_id, occurrence_id)
            canonical = _canonical_json(payload)
            existing = occurrences.get(key)
            if existing is None:
                occurrences[key] = (canonical, anchor_nodes, str(anchor_kind), {node})
                continue
            previous_canonical, previous_anchors, previous_kind, carriers = existing
            if previous_canonical != canonical:
                raise ValueError("Burns occurrence copies with one identity contain divergent payloads")
            if previous_anchors != anchor_nodes or previous_kind != anchor_kind:
                raise ValueError("Burns occurrence identity has conflicting anchor payload")
            carriers.add(node)

    for _, (_, anchor_nodes, _, carriers) in occurrences.items():
        if carriers != set(anchor_nodes):
            raise ValueError("Burns occurrence does not have a complete copy on every anchor placement")
    return occurrences


def _validate_report_for_write(
    report: Mapping[str, object],
    *,
    authoritative_nodes: set[int],
    occurrences: Mapping[tuple[str, str], tuple[str, tuple[int, ...], str, set[int]]],
) -> None:
    if report.get("schema") != MODULE_REPORT_SCHEMA:
        raise ValueError("refusing to write invalid Burns module report schema")
    if report.get("feature_inventory") != sorted(FEATURES):
        raise ValueError("Burns module report feature inventory does not match module")
    if report.get("cuc_compatibility") != reviewed_cuc_compatibility_payload():
        raise ValueError("Burns module report compatibility is not the exact reviewed CUC fingerprint")

    source_records = report.get("source_records")
    if not isinstance(source_records, list):
        raise ValueError("Burns module report source_records inventory is missing or invalid")
    source_ids: list[str] = []
    source_by_id: dict[str, dict[str, object]] = {}
    for row in source_records:
        if not isinstance(row, dict):
            raise ValueError("Burns module report source_records members must be objects")
        record_id = row.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Burns module report source record has invalid identity")
        if record_id in source_by_id:
            raise ValueError("Burns module report contains duplicate source record identities")
        source_ids.append(record_id)
        source_by_id[record_id] = row

    counts = report.get("counts")
    if not isinstance(counts, Mapping):
        raise ValueError("Burns module report counts are missing or invalid")
    if counts.get("records") != len(source_ids):
        raise ValueError("Burns module report source-record count is inconsistent")
    if counts.get("touched_nodes") != len(authoritative_nodes):
        raise ValueError("Burns module report touched-node count is inconsistent")
    if counts.get("selected_occurrences") != len(occurrences):
        raise ValueError("Burns module report selected-occurrence count is inconsistent")
    anchor_counts = dict(
        sorted(Counter(item[2] for item in occurrences.values()).items())
    )
    if counts.get("anchor_kinds") != anchor_counts:
        raise ValueError("Burns module report anchor-kind counts are inconsistent")

    alignment = report.get("alignment")
    if not isinstance(alignment, Mapping):
        raise ValueError("Burns module report embedded alignment report is missing")
    if alignment.get("schema") != "burns-cuc-alignment-report-v1":
        raise ValueError("Burns module report embedded alignment schema is invalid")
    if alignment.get("cuc_compatibility") != _reviewed_compatibility_identity():
        raise ValueError("Burns module report embedded alignment compatibility is invalid")
    alignment_counts = alignment.get("counts")
    if not isinstance(alignment_counts, Mapping):
        raise ValueError("Burns module report embedded alignment counts are invalid")
    if alignment_counts.get("records") != len(source_ids):
        raise ValueError("Burns module report embedded alignment record count is inconsistent")

    annotations = alignment.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError("Burns module report embedded alignment annotations are invalid")
    annotation_count = len(annotations)
    if counts.get("annotations") != annotation_count:
        raise ValueError("Burns module report annotation count is inconsistent")
    if alignment_counts.get("annotations") != annotation_count:
        raise ValueError("Burns module report embedded alignment annotation count is inconsistent")

    claimed_ids: list[str] = []
    disposition_counter: Counter[str] = Counter()
    selected_from_report: dict[tuple[str, str], tuple[dict[str, object], dict[str, object]]] = {}
    for annotation in annotations:
        if not isinstance(annotation, dict):
            raise ValueError("Burns module report alignment annotation is invalid")
        annotation_id = annotation.get("annotation_id")
        if not isinstance(annotation_id, str) or not annotation_id:
            raise ValueError("Burns module report alignment annotation identity is invalid")
        annotation_disposition = annotation.get("disposition")
        annotation_reason = annotation.get("reason")
        if not isinstance(annotation_disposition, str) or not annotation_disposition:
            raise ValueError("Burns module report alignment disposition is invalid")
        if not isinstance(annotation_reason, str) or not annotation_reason:
            raise ValueError("Burns module report alignment reason is invalid")
        disposition_counter[annotation_disposition] += 1

        record_ids = annotation.get("record_ids")
        if not isinstance(record_ids, list) or not all(isinstance(item, str) for item in record_ids):
            raise ValueError("Burns module report alignment record provenance is invalid")
        claimed_ids.extend(record_ids)

        alignment_occurrences = annotation.get("occurrences")
        if not isinstance(alignment_occurrences, list):
            raise ValueError("Burns module report alignment occurrences are invalid")
        for occurrence in alignment_occurrences:
            if not isinstance(occurrence, dict):
                raise ValueError("Burns module report alignment occurrence is invalid")
            occurrence_id = occurrence.get("occurrence_id")
            if not isinstance(occurrence_id, str) or not occurrence_id:
                raise ValueError("Burns module report occurrence identity is invalid")
            anchor_kind = occurrence.get("anchor_kind")
            anchor_nodes = occurrence.get("anchor_nodes")
            if anchor_kind is None:
                if anchor_nodes not in ([], ()):
                    raise ValueError("unselected Burns alignment occurrence has anchor nodes")
                continue
            if anchor_kind not in {"tablet", "line", "word_span"}:
                raise ValueError("Burns module report occurrence anchor kind is invalid")
            if not isinstance(anchor_nodes, list) or not anchor_nodes:
                raise ValueError("selected Burns alignment occurrence has invalid anchor nodes")
            key = (annotation_id, occurrence_id)
            if key in selected_from_report:
                raise ValueError("Burns module report contains duplicate selected occurrence identity")
            selected_from_report[key] = (annotation, occurrence)

    if len(claimed_ids) != len(set(claimed_ids)) or set(claimed_ids) != set(source_ids):
        raise ValueError("Burns module report source records are not exactly partitioned by annotations")

    disposition_counts = dict(sorted(disposition_counter.items()))
    if counts.get("alignment_dispositions") != disposition_counts:
        raise ValueError("Burns module report alignment disposition counts are inconsistent")
    if alignment_counts.get("dispositions") != disposition_counts:
        raise ValueError("Burns module report embedded alignment disposition counts are inconsistent")

    if set(selected_from_report) != set(occurrences):
        raise ValueError("Burns module and alignment report selected occurrence inventories disagree")

    for key, (annotation_entry, occurrence_entry) in selected_from_report.items():
        canonical, anchor_nodes, anchor_kind, _ = occurrences[key]
        payload = json.loads(canonical)
        if tuple(occurrence_entry["anchor_nodes"]) != anchor_nodes:
            raise ValueError("Burns module and alignment report occurrence anchors disagree")
        if occurrence_entry.get("anchor_kind") != anchor_kind:
            raise ValueError("Burns module and alignment report occurrence anchor kinds disagree")
        for field in _ALIGNMENT_OCCURRENCE_FIELDS:
            if payload.get(field) != occurrence_entry.get(field):
                raise ValueError(
                    f"Burns module and alignment report occurrence field {field} disagrees"
                )
        if payload.get("annotation_disposition") != annotation_entry.get("disposition"):
            raise ValueError("Burns module and alignment report annotation disposition disagrees")
        if payload.get("annotation_reason") != annotation_entry.get("reason"):
            raise ValueError("Burns module and alignment report annotation reason disagrees")

        payload_record_ids = payload.get("record_ids")
        payload_records = payload.get("source_records")
        if payload_record_ids != annotation_entry.get("record_ids"):
            raise ValueError("Burns module and alignment report record provenance disagrees")
        if not isinstance(payload_record_ids, list) or not isinstance(payload_records, list):
            raise ValueError("Burns node payload source record provenance is invalid")
        if len(payload_record_ids) != len(payload_records):
            raise ValueError("Burns node payload source record provenance length is inconsistent")

        for record_id, payload_record in zip(payload_record_ids, payload_records):
            if not isinstance(record_id, str) or not isinstance(payload_record, dict):
                raise ValueError("Burns node payload source record provenance is invalid")
            if payload_record.get("record_id") != record_id:
                raise ValueError("Burns node payload source record identity is inconsistent")
            report_record = source_by_id.get(record_id)
            if report_record is None:
                raise ValueError("Burns node payload references a missing report source record")
            if payload_record != report_record:
                raise ValueError("Burns node payload source record disagrees with report inventory")
            for field in _ANNOTATION_RECORD_FIELDS:
                if payload.get(field) != report_record.get(field):
                    raise ValueError(
                        f"Burns node annotation field {field} disagrees with source record"
                    )


def _validate_module_for_write(module: BurnsModuleData, report: Mapping[str, object]) -> None:
    if set(module.node_features) != set(FEATURES):
        raise ValueError("Burns TF module node-feature inventory is not the reviewed v1 inventory")
    if set(module.metadata) != set(FEATURES):
        raise ValueError("Burns TF module metadata inventory is not the reviewed v1 inventory")

    authoritative_nodes = set(module.node_features["burns_annotations"])
    parsed_by_node: dict[int, tuple[dict[str, object], ...]] = {}
    for node, value in module.node_features["burns_annotations"].items():
        parsed_by_node[node] = burns_node_annotations(value)

    occurrences = _validate_authoritative_placement(parsed_by_node)

    for feature in FEATURES:
        if set(module.node_features[feature]) != authoritative_nodes:
            raise ValueError(f"Burns projection node coverage differs for {feature}")
        if dict(module.metadata[feature]) != _expected_feature_metadata(feature):
            raise ValueError(f"invalid Burns TF metadata for {feature}")

    for node, parsed in parsed_by_node.items():
        expected_projections = _project_payloads(parsed)
        for feature, expected_value in expected_projections.items():
            actual_value = module.node_features[feature][node]
            if actual_value != expected_value:
                raise ValueError(
                    f"Burns projection {feature} differs from authoritative burns_annotations "
                    f"on node {node}"
                )

    _validate_report_for_write(
        report,
        authoritative_nodes=authoritative_nodes,
        occurrences=occurrences,
    )


def _owned_previous_module_files(output: Path) -> tuple[Path, ...]:
    """Prove that a nonempty prior TF inventory belongs to module-v1.

    A `burns_` filename prefix alone is never permission to replace a file.
    Identity metadata is cooperative ownership evidence, not a signed digest.
    """

    if not output.is_dir():
        return ()
    tf_entries = {path.name: path for path in output.iterdir() if path.suffix == ".tf"}
    unknown_tf = sorted(set(tf_entries) - _EXPECTED_TF_FILES)
    if unknown_tf:
        raise ValueError(
            "unknown TF files in Burns module-v1 output; refusing ownership: "
            + ", ".join(unknown_tf)
        )

    report_path = output / REPORT_FILE
    report_exists = report_path.exists() or report_path.is_symlink()
    if not tf_entries and not report_exists:
        return ()

    if set(tf_entries) != _EXPECTED_TF_FILES:
        raise ValueError(
            "incomplete prior Burns module-v1 feature inventory; refusing ownership"
        )
    for name, path in sorted(tf_entries.items()):
        if path.is_symlink() or not path.is_file():
            raise ValueError(
                f"invalid prior Burns module-v1 feature file: {name}"
            )
    if report_path.is_symlink() or not report_path.is_file():
        raise ValueError(
            "missing or non-regular Burns module-v1 report; refusing ownership"
        )
    try:
        prior_report = json.loads(report_path.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid prior Burns module-v1 report; refusing ownership") from exc
    if not isinstance(prior_report, dict) or (
        prior_report.get("schema") != MODULE_REPORT_SCHEMA
        or prior_report.get("feature_inventory") != sorted(FEATURES)
        or prior_report.get("cuc_compatibility") != reviewed_cuc_compatibility_payload()
    ):
        raise ValueError("prior Burns module-v1 report ownership identity mismatch")

    return tuple(output / name for name in sorted(_EXPECTED_TF_FILES | {REPORT_FILE}))


def _publish(stage: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    # Revalidate after staging: unknown files inserted during Fabric.save
    # must neither be silently removed nor accepted into the live output.
    old_owned = _owned_previous_module_files(output)

    with TemporaryDirectory(prefix=".burns-module-backup-", dir=output.parent) as backup_dir:
        backup = Path(backup_dir)
        moved_old: list[tuple[Path, Path]] = []
        installed: list[Path] = []
        try:
            for path in old_owned:
                saved = backup / path.name
                path.replace(saved)
                moved_old.append((saved, path))

            for name in sorted(_EXPECTED_TF_FILES | {REPORT_FILE}):
                staged = stage / name
                target = output / name
                staged.replace(target)
                installed.append(target)
        except Exception:
            for path in reversed(installed):
                if path.exists():
                    path.unlink()
            for saved, original in reversed(moved_old):
                if saved.exists():
                    saved.replace(original)
            raise


def write_burns_module(
    module: BurnsModuleData,
    report: dict[str, object],
    output_dir: str | Path,
    *,
    fabric_factory: Callable[..., _FabricLike] | None = None,
) -> bool:
    _validate_module_for_write(module, report)

    output = Path(output_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_dir():
        raise ValueError(f"Burns module output path is not a directory: {output}")
    # Reject incomplete/foreign output before constructing a Text-Fabric writer.
    _owned_previous_module_files(output)

    fabric = _make_fabric(fabric_factory)
    with TemporaryDirectory(prefix=".burns-module-stage-", dir=output.parent) as stage_dir:
        stage = Path(stage_dir)
        node_features, metadata = _plain_module(module)
        ok = bool(
            fabric.save(
                nodeFeatures=node_features,
                edgeFeatures={},
                metaData=metadata,
                location=str(stage),
                module="",
                silent="deep",
            )
        )
        if not ok:
            return False

        staged_tf = frozenset(
            path.name for path in stage.glob("*.tf") if path.is_file()
        )
        if staged_tf != _EXPECTED_TF_FILES:
            missing = sorted(_EXPECTED_TF_FILES - staged_tf)
            extra = sorted(staged_tf - _EXPECTED_TF_FILES)
            details = []
            if missing:
                details.append("missing=" + ",".join(missing))
            if extra:
                details.append("extra=" + ",".join(extra))
            raise RuntimeError(
                "Text-Fabric Burns module stage has unexpected feature inventory: "
                + "; ".join(details)
            )

        (stage / REPORT_FILE).write_text(
            _canonical_json(report) + "\n",
            encoding="utf-8",
        )
        _publish(stage, output)
    return True
