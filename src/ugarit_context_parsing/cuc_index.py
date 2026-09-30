from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

REVIEWED_CUC_REPOSITORY = "DT-UCPH/cuc"
REVIEWED_CUC_COMMIT = "ad69400f5446e1c8217af01659c7c10ab00c015b"
REVIEWED_CUC_VERSION = "0.2.8"
REVIEWED_CUC_MANIFEST_SHA256 = (
    "717e5b7f1c60b800e05f50f4cac27dac7562b45eecb48a8686c64cfab42a92ba"
)
REVIEWED_CUC_COMPATIBILITY_SCHEMA = "burns-cuc-compatibility-v1"


class CucCompatibilityError(ValueError):
    """Raised when a local CUC base cannot be trusted or indexed safely."""


@dataclass(frozen=True)
class CucFileFingerprint:
    size: int
    sha256: str


_REVIEWED_CUC_FILES = {
    "otype.tf": CucFileFingerprint(
        531,
        "d3ab2f599b7a1e1029608670c739b8439986a7be092d5d1b5eac5267a2ad554f",
    ),
    "oslots.tf": CucFileFingerprint(
        448752,
        "362c5bdd944cc6c2658634b83747f5796e61922bf81164e05ac8ebd579da85c8",
    ),
    "tablet.tf": CucFileFingerprint(
        3036,
        "db3429847e6daf67dd07452a72615ac999aa4419ea101b1e0312d294ceff05ef",
    ),
    "column.tf": CucFileFingerprint(
        1200,
        "0485fc45900d039a0227ad6c418530d1dfa373393bb3b5e9f0614066c26aaa17",
    ),
    "line.tf": CucFileFingerprint(
        20566,
        "a2e8122ffe274ff47b4b1f64f9a54dd623ec57d48bf95f74152bad35fff3fcf8",
    ),
    "g_cons.tf": CucFileFingerprint(
        124223,
        "7ac1a6a4c2641aa1b2579e8c204fcb93f18f9d6629c950054482cd2983dbcd80",
    ),
}
REVIEWED_CUC_FILES: Mapping[str, CucFileFingerprint] = MappingProxyType(
    _REVIEWED_CUC_FILES
)
_REVIEWED_CUC_COUNTS = {
    "sign": 146017,
    "column": 334,
    "line": 7616,
    "tablet": 279,
    "word": 27770,
}
REVIEWED_CUC_COUNTS: Mapping[str, int] = MappingProxyType(_REVIEWED_CUC_COUNTS)
REVIEWED_CUC_REQUIRED_FEATURES = ("column", "g_cons", "line", "tablet")
REVIEWED_CUC_SECTION_TYPES = ("tablet", "column", "line")
REVIEWED_CUC_SECTION_FEATURES = ("tablet", "column", "line")


@dataclass(frozen=True)
class CucCompatibility:
    repository: str
    commit: str
    version: str
    manifest_sha256: str
    files: tuple[tuple[str, CucFileFingerprint], ...]


@dataclass(frozen=True)
class CucTabletRow:
    node: int
    label: str


@dataclass(frozen=True)
class CucColumnRow:
    node: int
    tablet: str
    column: str


@dataclass(frozen=True)
class CucLineRow:
    node: int
    tablet: str
    column: str
    line: int
    words: tuple[int, ...]


@dataclass(frozen=True)
class CucStructuralSnapshot:
    counts: tuple[tuple[str, int], ...]
    section_types: tuple[str, ...]
    section_features: tuple[str, ...]
    tablets: tuple[CucTabletRow, ...]
    columns: tuple[CucColumnRow, ...]
    lines: tuple[CucLineRow, ...]
    word_g_cons: tuple[tuple[int, str], ...]
    # Optional for pure synthetic index fixtures. The public reviewed-CUC
    # loader always supplies the exact sign extent of every word.
    word_slots: tuple[tuple[int, tuple[int, ...]], ...] = ()


@dataclass(frozen=True)
class ReviewedCucIndex:
    compatibility: CucCompatibility | None
    tablet_nodes: Mapping[str, int]
    column_nodes: Mapping[tuple[str, str], int]
    line_nodes: Mapping[tuple[str, str, int], int]
    bare_line_candidates: Mapping[tuple[str, int], tuple[int, ...]]
    line_words: Mapping[int, tuple[int, ...]]
    word_g_cons: Mapping[int, str]
    # Exact word->sign extents from the independently loaded reviewed base.
    # Legacy/pure index fixtures may omit this, but native warp extension must
    # reject such an index rather than guessing identity from labels alone.
    word_slots: Mapping[int, tuple[int, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )


def reviewed_cuc_compatibility_payload() -> dict[str, object]:
    """Return a fresh canonical description of the exact reviewed CUC contract."""

    return {
        "schema": REVIEWED_CUC_COMPATIBILITY_SCHEMA,
        "repository": REVIEWED_CUC_REPOSITORY,
        "commit": REVIEWED_CUC_COMMIT,
        "version": REVIEWED_CUC_VERSION,
        "manifest_sha256": REVIEWED_CUC_MANIFEST_SHA256,
        "required_features": list(REVIEWED_CUC_REQUIRED_FEATURES),
        "node_type_counts": dict(sorted(REVIEWED_CUC_COUNTS.items())),
        "section_types": list(REVIEWED_CUC_SECTION_TYPES),
        "section_features": list(REVIEWED_CUC_SECTION_FEATURES),
        "required_files": {
            name: {"size": item.size, "sha256": item.sha256}
            for name, item in sorted(REVIEWED_CUC_FILES.items())
        },
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_sha256(files: Mapping[str, CucFileFingerprint]) -> str:
    payload = {
        name: {"sha256": item.sha256, "size": item.size}
        for name, item in files.items()
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_real_file(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise CucCompatibilityError(f"required CUC {label} is a disallowed symlink: {path.name}")
    if not path.exists():
        raise CucCompatibilityError(f"missing required CUC {label}: {path.name}")
    if not path.is_file():
        raise CucCompatibilityError(f"required CUC {label} is not a regular file: {path.name}")


def _verify_reviewed_cuc_files(path: str | Path) -> CucCompatibility:
    root = Path(path)
    if root.is_symlink():
        raise CucCompatibilityError(f"CUC TF directory is a disallowed symlink: {root}")
    if not root.is_dir():
        raise CucCompatibilityError(f"CUC TF path must be a directory: {root}")

    actual: dict[str, CucFileFingerprint] = {}
    for name, expected in REVIEWED_CUC_FILES.items():
        candidate = root / name
        _require_real_file(candidate, label="feature")
        size = candidate.stat().st_size
        sha256 = _sha256_file(candidate)
        if size != expected.size or sha256 != expected.sha256:
            raise CucCompatibilityError(
                "CUC fingerprint mismatch for "
                f"{name}: expected size={expected.size} sha256={expected.sha256}; "
                f"got size={size} sha256={sha256}"
            )
        actual[name] = CucFileFingerprint(size=size, sha256=sha256)

    manifest_sha256 = _manifest_sha256(actual)
    if manifest_sha256 != REVIEWED_CUC_MANIFEST_SHA256:
        raise CucCompatibilityError(
            "CUC required-files manifest fingerprint mismatch: "
            f"expected {REVIEWED_CUC_MANIFEST_SHA256}; got {manifest_sha256}"
        )

    return CucCompatibility(
        repository=REVIEWED_CUC_REPOSITORY,
        commit=REVIEWED_CUC_COMMIT,
        version=REVIEWED_CUC_VERSION,
        manifest_sha256=manifest_sha256,
        files=tuple(sorted(actual.items())),
    )


def _mapping_proxy(values: dict) -> Mapping:
    return MappingProxyType(dict(values))


def _normalize_column(value: str) -> str:
    column = value.strip()
    if not column:
        raise CucCompatibilityError("empty CUC column label after whitespace normalization")
    return column


def _build_index_from_snapshot(
    snapshot: CucStructuralSnapshot,
    *,
    expected_counts: Mapping[str, int],
    expected_section_types: tuple[str, ...],
    expected_section_features: tuple[str, ...],
    compatibility: CucCompatibility | None = None,
) -> ReviewedCucIndex:
    counts = dict(snapshot.counts)
    if counts != dict(expected_counts):
        raise CucCompatibilityError(
            f"CUC node-type count mismatch: expected {dict(expected_counts)!r}; got {counts!r}"
        )
    if snapshot.section_types != expected_section_types:
        raise CucCompatibilityError(
            "CUC section type mismatch: "
            f"expected {expected_section_types!r}; got {snapshot.section_types!r}"
        )
    if snapshot.section_features != expected_section_features:
        raise CucCompatibilityError(
            "CUC section feature mismatch: "
            f"expected {expected_section_features!r}; got {snapshot.section_features!r}"
        )

    if len(snapshot.tablets) != counts.get("tablet", -1):
        raise CucCompatibilityError("CUC tablet row count does not match otype count")
    if len(snapshot.columns) != counts.get("column", -1):
        raise CucCompatibilityError("CUC column row count does not match otype count")
    if len(snapshot.lines) != counts.get("line", -1):
        raise CucCompatibilityError("CUC line row count does not match otype count")
    if len(snapshot.word_g_cons) != counts.get("word", -1):
        raise CucCompatibilityError("CUC g_cons row count does not match word count")

    tablet_nodes: dict[str, int] = {}
    tablet_node_ids: set[int] = set()
    for row in sorted(snapshot.tablets, key=lambda item: (item.label, item.node)):
        if row.label in tablet_nodes:
            raise CucCompatibilityError(f"duplicate tablet label: {row.label!r}")
        if row.node in tablet_node_ids:
            raise CucCompatibilityError(f"duplicate tablet node id: {row.node}")
        tablet_nodes[row.label] = row.node
        tablet_node_ids.add(row.node)

    column_nodes: dict[tuple[str, str], int] = {}
    column_node_ids: set[int] = set()
    for row in sorted(snapshot.columns, key=lambda item: (item.tablet, item.column, item.node)):
        if row.tablet not in tablet_nodes:
            raise CucCompatibilityError(f"column references unknown tablet: {row.tablet!r}")
        column = _normalize_column(row.column)
        key = (row.tablet, column)
        if key in column_nodes:
            raise CucCompatibilityError(f"duplicate column key after normalization: {key!r}")
        if row.node in column_node_ids:
            raise CucCompatibilityError(f"duplicate column node id: {row.node}")
        column_nodes[key] = row.node
        column_node_ids.add(row.node)

    word_g_cons: dict[int, str] = {}
    for node, value in sorted(snapshot.word_g_cons):
        if node in word_g_cons:
            raise CucCompatibilityError(f"duplicate g_cons word node: {node}")
        word_g_cons[node] = value

    word_slots: dict[int, tuple[int, ...]] = {}
    for node, raw_slots in sorted(snapshot.word_slots):
        if node in word_slots:
            raise CucCompatibilityError(f"duplicate word oslots node: {node}")
        if node not in word_g_cons:
            raise CucCompatibilityError(f"word oslots references unknown word node: {node}")
        slots = tuple(int(slot) for slot in raw_slots)
        if not slots:
            raise CucCompatibilityError(f"word {node} has empty oslots extent")
        if slots != tuple(sorted(slots)) or len(slots) != len(set(slots)):
            raise CucCompatibilityError(f"word {node} has non-canonical oslots extent")
        if any(slot < 1 or slot > counts.get("sign", 0) for slot in slots):
            raise CucCompatibilityError(f"word {node} has out-of-range oslots extent")
        word_slots[node] = slots
    if word_slots and set(word_slots) != set(word_g_cons):
        raise CucCompatibilityError("CUC word oslots inventory does not match word count")

    line_nodes: dict[tuple[str, str, int], int] = {}
    line_node_ids: set[int] = set()
    line_words: dict[int, tuple[int, ...]] = {}
    bare_candidates: dict[tuple[str, int], list[int]] = {}

    for row in sorted(snapshot.lines, key=lambda item: item.node):
        if row.tablet not in tablet_nodes:
            raise CucCompatibilityError(f"line references unknown tablet: {row.tablet!r}")
        column = _normalize_column(row.column)
        if (row.tablet, column) not in column_nodes:
            raise CucCompatibilityError(
                f"line references unknown column: {(row.tablet, column)!r}"
            )
        key = (row.tablet, column, row.line)
        if key in line_nodes:
            raise CucCompatibilityError(f"duplicate exact line key: {key!r}")
        if row.node in line_node_ids:
            raise CucCompatibilityError(f"duplicate line node id: {row.node}")
        for word in row.words:
            if word not in word_g_cons:
                raise CucCompatibilityError(
                    f"line {row.node} references word {word} without g_cons inventory"
                )
        line_nodes[key] = row.node
        line_node_ids.add(row.node)
        line_words[row.node] = tuple(row.words)
        bare_candidates.setdefault((row.tablet, row.line), []).append(row.node)

    bare_line_candidates = {
        key: tuple(sorted(nodes))
        for key, nodes in sorted(bare_candidates.items())
    }

    return ReviewedCucIndex(
        compatibility=compatibility,
        tablet_nodes=_mapping_proxy(tablet_nodes),
        column_nodes=_mapping_proxy(column_nodes),
        line_nodes=_mapping_proxy(line_nodes),
        bare_line_candidates=_mapping_proxy(bare_line_candidates),
        line_words=_mapping_proxy(line_words),
        word_g_cons=_mapping_proxy(word_g_cons),
        word_slots=_mapping_proxy(word_slots),
    )


def _section_tuple(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _read_otext_section_config(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    section_types: tuple[str, ...] | None = None
    section_features: tuple[str, ...] | None = None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.rstrip("\r\n")
                if line.startswith("@sectionTypes="):
                    section_types = _section_tuple(line.split("=", 1)[1])
                elif line.startswith("@sectionFeatures="):
                    section_features = _section_tuple(line.split("=", 1)[1])
    except UnicodeDecodeError as exc:
        raise CucCompatibilityError("CUC otext.tf is not valid UTF-8") from exc

    if section_types is None or section_features is None:
        raise CucCompatibilityError("CUC otext.tf is missing sectionTypes/sectionFeatures metadata")
    return section_types, section_features


def _snapshot_from_tf(
    api: object,
    *,
    section_types: tuple[str, ...],
    section_features: tuple[str, ...],
) -> CucStructuralSnapshot:
    # Text-Fabric exposes corpus structure dynamically; keeping extraction in
    # one small adapter leaves the index builder pure and easy to challenge with
    # legal synthetic snapshots. Section-schema names come directly from
    # otext.tf because T.sectionFeatures exposes loaded feature-value maps in
    # Text-Fabric 13.1 rather than the metadata-name tuple.
    F = api.F  # type: ignore[attr-defined]
    E = api.E  # type: ignore[attr-defined]
    T = api.T  # type: ignore[attr-defined]
    L = api.L  # type: ignore[attr-defined]

    counts = tuple(
        sorted(
            (
                otype,
                len(tuple(F.otype.s(otype))),
            )
            for otype in REVIEWED_CUC_COUNTS
        )
    )

    tablets: list[CucTabletRow] = []
    for node in F.otype.s("tablet"):
        label = F.tablet.v(node)
        if label is None:
            raise CucCompatibilityError(f"CUC tablet node {node} has no tablet label")
        tablets.append(CucTabletRow(int(node), str(label)))

    columns: list[CucColumnRow] = []
    for node in F.otype.s("column"):
        section = T.sectionFromNode(node)
        if not section or len(section) < 2:
            raise CucCompatibilityError(f"CUC column node {node} has no tablet/column section")
        tablet, column = section[:2]
        columns.append(CucColumnRow(int(node), str(tablet), str(column)))

    lines: list[CucLineRow] = []
    for node in F.otype.s("line"):
        section = T.sectionFromNode(node)
        if not section or len(section) != 3:
            raise CucCompatibilityError(f"CUC line node {node} has invalid section: {section!r}")
        tablet, column, line = section
        try:
            line_number = int(line)
        except (TypeError, ValueError) as exc:
            raise CucCompatibilityError(
                f"CUC line node {node} has non-integer line number: {line!r}"
            ) from exc
        words = tuple(int(word) for word in L.d(node, otype="word"))
        lines.append(
            CucLineRow(
                node=int(node),
                tablet=str(tablet),
                column=str(column),
                line=line_number,
                words=words,
            )
        )

    word_g_cons = tuple(
        (int(node), "" if F.g_cons.v(node) is None else str(F.g_cons.v(node)))
        for node in F.otype.s("word")
    )
    word_slots = tuple(
        (
            int(node),
            tuple(sorted(int(slot) for slot in E.oslots.s(node))),
        )
        for node in F.otype.s("word")
    )

    return CucStructuralSnapshot(
        counts=counts,
        section_types=section_types,
        section_features=section_features,
        tablets=tuple(tablets),
        columns=tuple(columns),
        lines=tuple(lines),
        word_g_cons=word_g_cons,
        word_slots=word_slots,
    )


def build_reviewed_cuc_index(path: str | Path) -> ReviewedCucIndex:
    """Verify exact reviewed CUC bytes, then build deterministic lookup indexes."""

    supplied_root = Path(path)
    compatibility = _verify_reviewed_cuc_files(supplied_root)
    # Text-Fabric's location handling expects an absolute directory when a
    # caller supplies a relative path. Resolve only after the symlink and exact
    # byte checks above so path hardening remains authoritative.
    root = supplied_root.resolve()

    otext = root / "otext.tf"
    _require_real_file(otext, label="section metadata")
    section_types, section_features = _read_otext_section_config(otext)

    from tf.fabric import Fabric

    api = Fabric(locations=[str(root)], modules=[""], silent="deep").load(
        " ".join(REVIEWED_CUC_REQUIRED_FEATURES),
        silent="deep",
    )
    if not api:
        raise CucCompatibilityError(f"could not load reviewed CUC Text-Fabric from {root}")

    snapshot = _snapshot_from_tf(
        api,
        section_types=section_types,
        section_features=section_features,
    )
    index = _build_index_from_snapshot(
        snapshot,
        expected_counts=REVIEWED_CUC_COUNTS,
        expected_section_types=REVIEWED_CUC_SECTION_TYPES,
        expected_section_features=REVIEWED_CUC_SECTION_FEATURES,
        compatibility=compatibility,
    )
    return replace(index, compatibility=compatibility)
