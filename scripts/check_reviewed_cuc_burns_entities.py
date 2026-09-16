#!/usr/bin/env python3
"""Real reviewed CUC + Burns entity-extended warp smoke, using synthetic Burns rows.

This is an architecture/consumer test, not a real Burns-source coverage audit
and not the existing public CLI's still-v1 module. No derived data are kept.
"""
from __future__ import annotations

import argparse
import tempfile
from collections import Counter
from pathlib import Path

from tf.fabric import Fabric

from ugarit_context_parsing.alignment import BurnsAnchorKind, align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index
from ugarit_context_parsing.entity_extension import build_entity_extension
from ugarit_context_parsing.source import WorkbookRecord


def _unique_word(index):
    for (tablet, column, line), line_node in sorted(index.line_nodes.items()):
        words = index.line_words[line_node]
        values = tuple(index.word_g_cons[word] for word in words)
        counts = Counter(values)
        for word, value in zip(words, values):
            if (
                value and not any(ch.isspace() for ch in value)
                and not value.endswith(("*", "†", "!", "?"))
                and counts[value] == 1
            ):
                return tablet, column, line, word, value
    raise AssertionError("reviewed CUC has no unique exact-match word")


def _record(workbook: int, tablet: str, column: str, line: int, headword: str):
    return WorkbookRecord(
        source_file=f"{workbook:02d} Synthetic/Worksheet 1.csv",
        source_row=1,
        source_page=1,
        section="Section α" if workbook == 1 else "Section α1",
        root="SYNROOT" if workbook == 9 else "",
        headword=headword,
        ktu=tablet.removeprefix("KTU "),
        references=f"{column}.{line}",
        locus="SYN",
        room="SYNROOM",
        point="SYNPOINT",
        depth="SYNDEPTH",
        disputed="",
        comments="synthetic smoke; no source redistribution",
    )


def _hits(api, query: str) -> set[int]:
    result = api.S.search(query, silent="deep")
    return {row[0] for row in result}


def run(cuc_dir: Path) -> None:
    from cfabric_mcp import tools
    from cfabric_mcp.corpus_manager import corpus_manager

    cuc = cuc_dir.resolve()
    index = build_reviewed_cuc_index(cuc)  # exact reviewed on-disk fingerprint
    tablet, column, line, word, label = _unique_word(index)
    source = normalize_workbook_records(
        (_record(1, tablet, column, line, label),
         _record(9, tablet, column, line, label))
    )
    alignments = align_burns_source(source, index)
    assert len(alignments) == 2
    for alignment in alignments:
        assert len(alignment.occurrences) == 1
        occurrence = alignment.occurrences[0]
        assert occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
        assert occurrence.anchor_nodes == (word,)

    base = Fabric(locations=[str(cuc)], modules=[""], silent="deep").loadAll(silent="deep")
    if base is None:
        raise AssertionError("reviewed CUC could not be loaded")
    old_max, old_slots = base.F.otype.maxNode, base.F.otype.maxSlot
    word_nodes = tuple(base.F.otype.s("word"))
    print(
        "CUC warp diagnostics: "
        f"actual_slots={old_slots} actual_max_node={old_max} "
        f"first_word={min(word_nodes)} indexed_first_gcons={min(index.word_g_cons)} "
        f"indexed_max_word={max(index.word_g_cons)} "
        f"indexed_max_line={max(index.line_nodes.values())} "
        f"indexed_max_column={max(index.column_nodes.values())} "
        f"indexed_max_tablet={max(index.tablet_nodes.values())} "
        f"word_count={len(word_nodes)} indexed_word_count={len(index.word_g_cons)}",
        flush=True,
    )
    old_word_slots = tuple(base.E.oslots.s(word))
    tablet_node = index.tablet_nodes[tablet]
    extension = build_entity_extension(source, alignments, index, base)
    if len(extension.occurrence_nodes) != 2:
        raise AssertionError("overlapping Burns occurrences were collapsed")
    entities = set(extension.occurrence_nodes)
    if entities != {old_max + 1, old_max + 2}:
        raise AssertionError("entity node IDs unexpectedly changed")
    if extension.node_features["burns_locus"] != {tablet_node: "SYN"}:
        raise AssertionError("findspot was not scoped to exactly the tablet")

    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary) / "entity-overlay"
        saved = Fabric(locations=[], modules=[], silent="deep").save(
            nodeFeatures={key: dict(values) for key, values in extension.node_features.items()},
            edgeFeatures={key: dict(values) for key, values in extension.edge_features.items()},
            metaData={key: dict(values) for key, values in extension.metadata.items()},
            location=str(directory), module="", silent="deep",
        )
        if not saved:
            raise AssertionError("Text-Fabric rejected the entity extension")
        base_info = corpus_manager.load(str(cuc), name="reviewed-cuc-entity-base")
        combined_info = corpus_manager.load(
            [str(cuc), str(directory)], name="reviewed-cuc-with-native-burns-entities"
        )
        _, api = corpus_manager.get("reviewed-cuc-with-native-burns-entities")
        if base_info.max_slot != combined_info.max_slot or combined_info.max_slot != old_slots:
            raise AssertionError("Burns extension changed CUC sign slots")
        if combined_info.max_node != old_max + 2:
            raise AssertionError("Burns extension has incorrect additional-node count")
        if (api.F.otype.v(word), api.F.otype.v(tablet_node)) != ("word", "tablet"):
            raise AssertionError("Burns extension remapped existing CUC nodes")
        if tuple(api.E.oslots.s(word)) != old_word_slots:
            raise AssertionError("Burns extension changed CUC word extent")
        if {api.F.otype.v(node) for node in entities} != {"entity"}:
            raise AssertionError("annotation occurrences are not real TF entity nodes")
        divine = _hits(api, "entity burns_category=divine_name")
        actions = _hits(api, "entity burns_category=cultic_action")
        roots = _hits(api, "entity burns_root=SYNROOT")
        if len(divine) != 1 or len(actions) != 1 or actions != roots or divine == actions:
            raise AssertionError("native TF entity/category/root queries lost overlap")
        for entity in entities:
            if api.F.burns_headword.v(entity) != label:
                raise AssertionError("Burns source headword not on its occurrence entity")
            if tuple(api.E.oslots.s(entity)) != old_word_slots:
                raise AssertionError("Burns entity has incorrect sign extent")
            if api.F.burns_locus.v(entity) is not None:
                raise AssertionError("tablet findspot leaked onto annotation entity")
        if _hits(api, "tablet burns_locus=SYN") != {tablet_node}:
            raise AssertionError("tablet-level findspot is not natively queryable")
        if api.F.burns_locus.v(word) is not None:
            raise AssertionError("tablet-level findspot leaked onto word")
        if "burns_annotations" in api.Fall() or "burns_source_row" in api.Fall():
            raise AssertionError("JSON blobs or per-row provenance leaked into TF")
        response = tools.search(
            "entity burns_category=divine_name",
            corpus="reviewed-cuc-with-native-burns-entities", limit=20,
        )
        if "error" in response:
            raise AssertionError(f"cfabric-mcp rejected native entity search: {response!r}")
        returned = {int(item["node"]) for row in response.get("results", []) for item in row}
        if returned != divine:
            raise AssertionError(f"cfabric-mcp returned wrong entity nodes: {returned!r} != {divine!r}")
    print("Reviewed CUC + two overlapping native Burns entity nodes + tablet findspot + MCP search: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cuc_dir", type=Path)
    args = parser.parse_args()
    run(args.cuc_dir)


if __name__ == "__main__":
    main()
