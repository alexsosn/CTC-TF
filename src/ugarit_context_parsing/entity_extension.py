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
from .tablet_findspots import BurnsTabletFindspots, derive_tablet_findspots

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
    findspot_audit: BurnsTabletFindspots


def _verify_loaded_warp(index: ReviewedCucIndex, api: _Api) -> None:
    """Reject a different in-memory CUC graph before overriding warp features.

    This is a structural cross-check, NOT a substitute for the public CLI's
    reviewed on-disk SHA-256 fingerprint gate. It prevents an independently
    constructed index from being accidentally paired with a different TF API.
    """
    if not index.word_g_cons or not index.tablet_nodes:
        raise ValueError("CUC warp/index mismatch: missing indexed text or tablets")
    # g_cons is a sparse lexical feature: its first populated word need not be
    # the corpus's first word. Determine the sign/word boundary from the warp,
    # then verify the observed CUC slot count against that independent boundary.
    word_nodes = api.F.otype.s("word")
    if not word_nodes:
        raise ValueError("CUC warp/index mismatch: no word nodes")
    expected_slot_max = min(word_nodes) - 1
    expected_node_max = max(
        *index.word_g_cons,
        *index.line_nodes.values(),
        *index.column_nodes.values(),
        *index.tablet_nodes.values(),
    )
    if (api.F.otype.maxSlot, api.F.otype.maxNode) != (
        expected_slot_max, expected_node_max
    ):
        raise ValueError("CUC warp/index mismatch: slot or node count differs")
    for nodes, node_type in (
        (index.word_g_cons, "word"),
        (index.line_nodes.values(), "line"),
        (index.column_nodes.values(), "column"),
        (index.tablet_nodes.values(), "tablet"),
    ):
        if any(api.F.otype.v(node) != node_type for node in nodes):
            raise ValueError(f"CUC warp/index mismatch: {node_type} node type differs")
    if any(
        api.F.g_cons.v(node) != transcription
        for node, transcription in index.word_g_cons.items()
    ):
        raise ValueError("CUC warp/index mismatch: word transcription differs")


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
    _verify_loaded_warp(index, api)
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
            if not word_slots or any(slot < 1 or slot > max_slot for slot in word_slots):
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

    findspots = derive_tablet_findspots(source, index)
    features = {
        "otype": otype,
        **node_values,
        **{name: dict(values) for name, values in findspots.node_features.items() if values},
    }
    metadata = {
        name: {
            "valueType": "str",
            "description": "Burns lexical occurrence entity (extended CUC warp; experimental)",
        }
        for name in features
    }
    for name in findspots.node_features:
        if name in features:
            metadata[name]["description"] = "Consistent Burns observation on CUC tablet only"
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
        findspot_audit=findspots,
    )
