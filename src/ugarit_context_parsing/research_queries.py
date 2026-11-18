"""Read-only researcher queries over a loaded CUC + Burns Text-Fabric API.

Burns feature-module v3 stores each exact lexical occurrence on an existing CUC
word, with one numbered family of features per overlapping occurrence. This
module enumerates all loaded families without reading private report JSON,
creating new TF nodes, or trying to repair uncertain lexical alignments.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from .feature_module import SCHEMA, _FINDSPOT_FIELDS


_OCCURRENCE_FEATURE = re.compile(r"^burns_occurrence_id_([1-9][0-9]*)$")
_REQUIRED_LANE_FIELDS = (
    "burns_occurrence_id",
    "burns_annotation_id",
    "burns_headword",
    "burns_match_rule",
    "burns_category",
    "burns_semantic_status",
    "burns_worksheet_role",
    "burns_section",
    "burns_span_length",
)


@dataclass(frozen=True)
class BurnsOccurrence:
    """One exact Burns lexical occurrence, not a lemma or inferred mention."""

    carrier_node: int
    lane: int
    span_nodes: tuple[int, ...]
    occurrence_id: str
    annotation_id: str
    headword: str
    category: str
    semantic_status: str
    match_rule: str
    worksheet_role: str
    section: str
    root: str | None


def iter_burns_occurrences(
    api,
    *,
    category: str | None = None,
    semantic_status: str | None = None,
) -> Iterator[BurnsOccurrence]:
    """Enumerate exact occurrences in every loaded Burns feature-module lane.

    Pass a Text-Fabric API loaded from the ordered locations
    [reviewed CUC TF, Burns feature-module]. Filters are exact source-feature
    values; negative/homograph statuses are not silently omitted. An annotation
    referenced at multiple places yields multiple distinct occurrence IDs.

    This API exposes restricted, source-derived Burns headwords/provenance.
    Keep results local under the source licence.
    """
    available = set(api.Fall())
    lanes = sorted(
        int(match.group(1))
        for name in available
        if (match := _OCCURRENCE_FEATURE.fullmatch(name))
    )
    if not lanes:
        # A legitimate v3 overlay may have only tablet-level findspot features
        # when none of its lexical citations align exactly. Distinguish it from
        # a base-only or legacy overlay via the writer's feature metadata.
        if any(
            name in available
            and api.Fs(name).meta.get("moduleSchema") == SCHEMA
            for name in _FINDSPOT_FIELDS
        ):
            return
        raise ValueError(
            "Burns feature-module occurrence features are not loaded; "
            "load the reviewed CUC first and the v3 Burns module second"
        )

    edges = set(api.Eall())
    result: list[BurnsOccurrence] = []
    for lane in lanes:
        missing = [
            f"{base}_{lane}" for base in _REQUIRED_LANE_FIELDS
            if f"{base}_{lane}" not in available
        ]
        if missing:
            raise ValueError(f"incomplete Burns occurrence lane {lane}: {', '.join(missing)}")

        def value(field: str, carrier: int):
            return api.Fs(f"{field}_{lane}").v(carrier)

        root_name = f"burns_root_{lane}"
        span_name = f"burns_span_{lane}"

        for carrier, occurrence_id in api.Fs(f"burns_occurrence_id_{lane}").items():
            observed_category = value("burns_category", carrier)
            observed_status = value("burns_semantic_status", carrier)
            if category is not None and observed_category != category:
                continue
            if semantic_status is not None and observed_status != semantic_status:
                continue

            length = value("burns_span_length", carrier)
            if not isinstance(length, int) or length < 1:
                raise ValueError(f"invalid Burns span length at word {carrier}, lane {lane}")
            if api.F.otype.v(carrier) != "word":
                raise ValueError(f"Burns occurrence carrier {carrier} is not a CUC word")

            targets = tuple(api.Es(span_name).f(carrier)) if span_name in edges else ()
            if length == 1 and targets:
                raise ValueError(f"single-word Burns occurrence has span edges at {carrier}, lane {lane}")
            if length > 1 and not targets:
                raise ValueError(f"missing Burns span edges at {carrier}, lane {lane}")
            if len(set(targets)) != len(targets) or carrier in targets:
                raise ValueError(f"duplicate/loop Burns span edge at {carrier}, lane {lane}")
            if any(api.F.otype.v(target) != "word" for target in targets):
                raise ValueError(f"Burns span contains a non-word at {carrier}, lane {lane}")

            # Text-Fabric's canonical ordering uses the parent warp and does not
            # assume that word node identifiers always increase with text order.
            span = tuple(api.N.sortNodes((carrier, *targets)))
            if len(span) != length or span[0] != carrier:
                raise ValueError(f"inconsistent Burns span at word {carrier}, lane {lane}")

            required_values = {
                name: value(name, carrier)
                for name in (
                    "burns_annotation_id", "burns_headword", "burns_match_rule",
                    "burns_worksheet_role", "burns_section",
                )
            }
            if occurrence_id is None or any(v is None for v in required_values.values()):
                raise ValueError(f"incomplete Burns occurrence at word {carrier}, lane {lane}")

            result.append(BurnsOccurrence(
                carrier_node=carrier,
                lane=lane,
                span_nodes=span,
                occurrence_id=occurrence_id,
                annotation_id=required_values["burns_annotation_id"],
                headword=required_values["burns_headword"],
                category=observed_category,
                semantic_status=observed_status,
                match_rule=required_values["burns_match_rule"],
                worksheet_role=required_values["burns_worksheet_role"],
                section=required_values["burns_section"],
                root=value("burns_root", carrier) if root_name in available else None,
            ))

    yield from sorted(result, key=lambda occurrence: (occurrence.carrier_node, occurrence.lane))
