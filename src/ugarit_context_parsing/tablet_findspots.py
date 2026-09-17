"""Conservative tablet-scoped Burns excavation observations.

The Workbooks' row fields are observations, not token annotations. A tablet
gets a scalar only when *every* mapped Burns row for that tablet explicitly
agrees. Conflicting or partially missing evidence is retained in a local
sidecar manifest rather than silently promoted to a tablet-wide claim. This
helper does not invent CUC fragment nodes or merge Appendix evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .annotations import BurnsSourceRecord, NormalizedBurnsSource
from .cuc_index import ReviewedCucIndex
from .identifiers import normalize_cuc_tablet

_FIELDS: Mapping[str, str] = MappingProxyType(
    {
        "locus": "burns_locus",
        "room": "burns_room",
        "point": "burns_point",
        "depth": "burns_depth",
        "disputed": "burns_disputed",
    }
)


@dataclass(frozen=True)
class BurnsTabletFindspots:
    node_features: Mapping[str, Mapping[int, str]]
    conflicts: Mapping[int, Mapping[str, tuple[str, ...]]]
    incomplete: Mapping[int, tuple[str, ...]]
    unmapped_record_ids: tuple[str, ...]


def derive_tablet_findspots(
    source: NormalizedBurnsSource,
    index: ReviewedCucIndex,
) -> BurnsTabletFindspots:
    """Return only fully corroborated per-tablet scalar features.

    Empty source cells do not count as agreement: a value observed for only
    one putative fragment cannot be asserted as the whole tablet's value.
    Distinct nonempty values are explicit conflicts; missing observations
    are separately recorded as incomplete. All original rows remain in
    `source` and must be persisted only in the local, licensed report.
    """
    by_tablet: dict[int, list[BurnsSourceRecord]] = {}
    unmapped: list[str] = []
    for record in source.records:
        tablet = normalize_cuc_tablet(record.ktu)
        node = index.tablet_nodes.get(tablet) if tablet else None
        if node is None:
            unmapped.append(record.record_id)
        else:
            by_tablet.setdefault(node, []).append(record)

    features: dict[str, dict[int, str]] = {
        name: {} for name in _FIELDS.values()
    }
    conflicts: dict[int, dict[str, tuple[str, ...]]] = {}
    incomplete: dict[int, tuple[str, ...]] = {}

    for tablet, records in sorted(by_tablet.items()):
        missing_fields: list[str] = []
        for attr, feature in _FIELDS.items():
            observed = tuple(getattr(record, attr).strip() for record in records)
            nonempty = tuple(sorted({value for value in observed if value}))
            if len(nonempty) > 1:
                conflicts.setdefault(tablet, {})[feature] = nonempty
            elif len(nonempty) == 1 and all(observed):
                features[feature][tablet] = nonempty[0]
            elif len(nonempty) == 1 and not all(observed):
                missing_fields.append(feature)
        if missing_fields:
            incomplete[tablet] = tuple(sorted(missing_fields))

    return BurnsTabletFindspots(
        node_features=MappingProxyType(
            {name: MappingProxyType(dict(sorted(values.items())))
             for name, values in sorted(features.items())}
        ),
        conflicts=MappingProxyType(
            {node: MappingProxyType(dict(sorted(values.items())))
             for node, values in sorted(conflicts.items())}
        ),
        incomplete=MappingProxyType(dict(sorted(incomplete.items()))),
        unmapped_record_ids=tuple(sorted(unmapped)),
    )
