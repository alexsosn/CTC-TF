"""Native scalar predicates derived from verified Burns-to-CUC word alignments.

This is an isolated *projection*, not yet the public v2 Text-Fabric module.
Existing feature-only CUC modules cannot introduce annotation/fragment nodes;
the integration, provenance/report and publication migration remain #68 gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .alignment import (
    BurnsAlignmentConfidence,
    BurnsAlignmentDisposition,
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
    build_alignment_report,
)
from .annotations import BurnsSemanticStatus, NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex

# Burns 2003, volume I, chapter 5, p. 187: the ordinal is source-defined.
# A source's basename is retained as provenance but NEVER parsed heuristically
# to determine the thematic class.
CATEGORY_FEATURES: Mapping[int, str] = MappingProxyType(
    {
        1: "burns_in_divine_name",
        2: "burns_in_personal_name",
        3: "burns_in_geographical_name",
        4: "burns_in_cultic_jargon",
        5: "burns_in_cultic_commodity",
        6: "burns_in_cultic_location",
        7: "burns_in_cultic_time_event",
        8: "burns_in_cultic_personnel",
        9: "burns_in_cultic_action",
    }
)

# Category predicates indicate a source classification of an exact match;
# excluded homographs/unsupported source sections must not become hits.
_EXCLUDED_STATUSES = frozenset(
    {BurnsSemanticStatus.HOMOGRAPH_EXCLUDED, BurnsSemanticStatus.UNSUPPORTED}
)


@dataclass(frozen=True)
class NativeBurnsFeatures:
    """Candidate TF node features, plus collisions that must stay in a sidecar.

    Feature values are individual strings or integer 1, never JSON/CSV lists.
    Absent `burns_headword` or `burns_root` at a collision means *unknown*, not
    an arbitrary selected value. Full occurrence provenance belongs in the
    eventual local report; this projection does not lose the source objects.
    """

    node_features: Mapping[str, Mapping[int, str | int]]
    headword_collisions: Mapping[int, tuple[str, ...]]
    root_collisions: Mapping[int, tuple[str, ...]]


def _scalar_projection(
    candidates: Mapping[int, set[str]],
) -> tuple[dict[int, str], dict[int, tuple[str, ...]]]:
    values: dict[int, str] = {}
    conflicts: dict[int, tuple[str, ...]] = {}
    for node in sorted(candidates):
        distinct = tuple(sorted(candidates[node]))
        if len(distinct) == 1:
            values[node] = distinct[0]
        elif len(distinct) > 1:
            conflicts[node] = distinct
    return values, conflicts


def derive_native_features(
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> NativeBurnsFeatures:
    """Build collision-safe, queryable predicates without modifying CUC warp.

    Integrity is checked against the source, not the caller's claim: the
    existing alignment report gate rejects missing, extra or forged alignment
    anchors before any feature is returned. Only exact lexical spans produce
    word predicates. For multiword spans, category membership applies to all
    participating words, but the *phrase headword/root* is never attached to
    individual constituent words. Ambiguous/structural anchors give no lexical
    hit. Category and scalar output always have deterministic node ordering.
    """
    build_alignment_report(source, alignments, index)
    by_id = {alignment.annotation_id: alignment for alignment in alignments}
    categories: dict[str, dict[int, int]] = {
        name: {} for name in CATEGORY_FEATURES.values()
    }
    headwords: dict[int, set[str]] = {}
    roots: dict[int, set[str]] = {}

    for annotation in sorted(source.annotations, key=lambda item: item.annotation_id):
        try:
            category_feature = CATEGORY_FEATURES[annotation.workbook_number]
        except KeyError as exc:
            raise ValueError(
                f"unreviewed Burns workbook number: {annotation.workbook_number}"
            ) from exc
        if annotation.semantic_status in _EXCLUDED_STATUSES:
            continue

        for occurrence in by_id[annotation.annotation_id].occurrences:
            if not (
                occurrence.disposition is BurnsAlignmentDisposition.ALIGNED
                and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
                and occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
                and occurrence.anchor_nodes
            ):
                continue

            for node in occurrence.anchor_nodes:
                categories[category_feature][node] = 1

            if len(occurrence.anchor_nodes) != 1:
                continue
            word = occurrence.anchor_nodes[0]
            if annotation.headword:
                headwords.setdefault(word, set()).add(annotation.headword)
            if annotation.root:
                roots.setdefault(word, set()).add(annotation.root)

    headword_values, headword_conflicts = _scalar_projection(headwords)
    root_values, root_conflicts = _scalar_projection(roots)
    features: dict[str, dict[int, str | int]] = {
        **categories,
        "burns_headword": headword_values,
        "burns_root": root_values,
    }
    return NativeBurnsFeatures(
        node_features=MappingProxyType(
            {
                name: MappingProxyType(dict(sorted(values.items())))
                for name, values in sorted(features.items())
            }
        ),
        headword_collisions=MappingProxyType(headword_conflicts),
        root_collisions=MappingProxyType(root_conflicts),
    )
