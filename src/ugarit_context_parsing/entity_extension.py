"""Experimental extended CUC warp for first-class Burns occurrence entities.

This is an architecture proof, NOT the current CLI/publisher's v2 output.
An ordinary feature-only TF module cannot add node types. This builder
produces a complete replacement `otype`/`oslots` warp for local composition;
consumer validation, full source scope, local reporting and safe publication
must be completed separately before exposing it as a supported product.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol

from .alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentDisposition,
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
    build_alignment_report,
)
from .annotations import NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex

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


class _Api(Protocol):
    F: object
    E: object


@dataclass(frozen=True)
class BurnsEntityExtension:
    node_features: Mapping[str, Mapping[int, str]]
    edge_features: Mapping[str, Mapping[int, set[int]]]
    metadata: Mapping[str, Mapping[str, str]]
    # Local sidecar linkage, never a serialized lexical/archaeological field.
    occurrence_nodes: Mapping[int, tuple[str, str]]


def build_entity_extension(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
    api: _Api,
) -> BurnsEntityExtension:
    """Append uniquely aligned Burns entities without renumbering CUC nodes.

    Entity extent consists of the union of CUC sign slots occupied by each
    unambiguously matched word. Overlap is encoded by distinct entity nodes,
    not by serializing lists of annotations onto shared word nodes.
    """
    build_alignment_report(source, alignments, index)
    old_max = api.F.otype.maxNode
    max_slot = api.F.otype.maxSlot
    otype = {node: api.F.otype.v(node) for node in range(1, old_max + 1)}
    oslots = {
        node: set(api.E.oslots.s(node))
        for node in range(max_slot + 1, old_max + 1)
    }
    annotations = {annotation.annotation_id: annotation for annotation in source.annotations}
    node_values: dict[str, dict[int, str]] = {
        name: {}
        for name in (
            "burns_headword",
            "burns_root",
            "burns_category",
            "burns_semantic_status",
            "burns_worksheet_role",
            "burns_section",
        )
    }
    occurrence_nodes: dict[int, tuple[str, str]] = {}

    selected = sorted(
        (
            (alignment.annotation_id, occurrence)
            for alignment in alignments
            for occurrence in alignment.occurrences
            if occurrence.disposition is BurnsAlignmentDisposition.ALIGNED
            and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
            and occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
            and occurrence.anchor_nodes
        ),
        key=lambda pair: (pair[0], pair[1].target_ordinal, pair[1].occurrence_id),
    )
    for ordinal, (annotation_id, occurrence) in enumerate(selected, 1):
        annotation = annotations[annotation_id]
        try:
            category = CATEGORY_NAMES[annotation.workbook_number]
        except KeyError as exc:
            raise ValueError("unsupported Burns workbook category") from exc
        node = old_max + ordinal
        slots: set[int] = set()
        for word in occurrence.anchor_nodes:
            if api.F.otype.v(word) != "word":
                raise ValueError("Burns lexical anchor is not a CUC word")
            word_slots = set(api.E.oslots.s(word))
            if not word_slots or not word_slots.issubset(set(range(1, max_slot + 1))):
                raise ValueError("Burns lexical anchor contains invalid CUC sign slots")
            slots.update(word_slots)
        if not slots:
            raise ValueError("Burns entity cannot be empty")
        otype[node] = "entity"
        oslots[node] = slots
        occurrence_nodes[node] = (annotation_id, occurrence.occurrence_id)
        node_values["burns_headword"][node] = annotation.headword
        if annotation.root:
            node_values["burns_root"][node] = annotation.root
        node_values["burns_category"][node] = category
        node_values["burns_semantic_status"][node] = annotation.semantic_status.value
        node_values["burns_worksheet_role"][node] = annotation.worksheet_role.value
        node_values["burns_section"][node] = annotation.section

    features = {"otype": otype, **node_values}
    metadata = {
        name: {
            "valueType": "str",
            "description": "Burns lexical occurrence entity (extended CUC warp; experimental)",
        }
        for name in features
    }
    metadata["otype"] = {"valueType": "str", "description": "CUC node types plus Burns entities"}
    metadata["oslots"] = {"valueType": "int", "description": "CUC sign extents plus Burns entities"}
    return BurnsEntityExtension(
        node_features=MappingProxyType(
            {name: MappingProxyType(dict(sorted(values.items()))) for name, values in sorted(features.items())}
        ),
        edge_features=MappingProxyType({"oslots": MappingProxyType(dict(sorted(oslots.items())))}),
        metadata=MappingProxyType(
            {name: MappingProxyType(values) for name, values in sorted(metadata.items())}
        ),
        occurrence_nodes=MappingProxyType(dict(sorted(occurrence_nodes.items()))),
    )
