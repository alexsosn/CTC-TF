#!/usr/bin/env python3
"""Reviewed CUC + primary feature-only Burns module + cfabric-mcp smoke.

Uses synthetic Burns rows against the exact reviewed CUC. No Burns source data
is downloaded or redistributed by this consumer contract.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

from tf.fabric import Fabric

from ugarit_context_parsing.alignment import BurnsAnchorKind, align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cli import main as materialize_cli
from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index
from ugarit_context_parsing.feature_module import REPORT_FILE, SCHEMA
from ugarit_context_parsing.source import WORKBOOK_FIELDS, WorkbookRecord


def _safe_token(value: str) -> bool:
    return bool(value) and not any(ch.isspace() for ch in value) and not value.endswith(("*", "†", "!", "?"))


def _unique_word(index):
    for (tablet, column, line), line_node in sorted(index.line_nodes.items()):
        words = index.line_words[line_node]
        values = tuple(index.word_g_cons[word] for word in words)
        counts = Counter(values)
        for word, value in zip(words, values, strict=True):
            if _safe_token(value) and counts[value] == 1:
                return tablet, column, line, word, value
    raise AssertionError("reviewed CUC has no unique exact-match word")


def _unique_phrase(index):
    for (tablet, column, line), line_node in sorted(index.line_nodes.items()):
        words = index.line_words[line_node]
        values = tuple(index.word_g_cons[word] for word in words)
        pairs = tuple(zip(values, values[1:], strict=False))
        counts = Counter(pairs)
        for offset, pair in enumerate(pairs):
            if all(_safe_token(value) for value in pair) and counts[pair] == 1:
                return tablet, column, line, (words[offset], words[offset + 1]), " ".join(pair)
    raise AssertionError("reviewed CUC has no unique exact-match two-word phrase")


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
        comments="synthetic feature-only consumer smoke",
    )


def _write_rows(root: Path, rows: tuple[WorkbookRecord, ...]) -> None:
    for row in rows:
        target = root / row.source_file
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=WORKBOOK_FIELDS)
            writer.writeheader()
            writer.writerow({name: getattr(row, name) for name in WORKBOOK_FIELDS})


def _returned_nodes(response) -> set[int]:
    return {
        int(item["node"])
        for row in response.get("results", [])
        for item in row
    }


def run(cuc_dir: Path) -> None:
    from cfabric_mcp import tools
    from cfabric_mcp.corpus_manager import corpus_manager

    cuc = cuc_dir.resolve()
    index = build_reviewed_cuc_index(cuc)
    tablet, column, line, word, label = _unique_word(index)
    p_tablet, p_column, p_line, phrase_words, phrase_label = _unique_phrase(index)

    rows = (
        _record(1, tablet, column, line, label),
        _record(9, tablet, column, line, label),
        _record(4, p_tablet, p_column, p_line, phrase_label),
    )
    source = normalize_workbook_records(rows)
    alignments = align_burns_source(source, index)
    exact = [
        occurrence
        for alignment in alignments
        for occurrence in alignment.occurrences
        if occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
    ]
    if len(exact) != 3:
        raise AssertionError(f"expected three exact synthetic occurrences, got {len(exact)}")

    base = Fabric(locations=[str(cuc)], modules=[""], silent="deep").loadAll(silent="deep")
    if base is None:
        raise AssertionError("reviewed CUC could not be loaded")
    old_max, old_slots = base.F.otype.maxNode, base.F.otype.maxSlot
    old_word_slots = tuple(base.E.oslots.s(word))
    tablet_node = index.tablet_nodes[tablet]

    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        source_root = temp / "Workbooks"
        _write_rows(source_root, rows)
        directory = temp / "burns-feature"

        if materialize_cli([
            "module", str(source_root), "--input-format", "csv",
            "--cuc", str(cuc), "--output", str(directory),
        ]) != 0:
            raise AssertionError("primary feature-only Burns module CLI refused reviewed CUC")

        report = json.loads((directory / REPORT_FILE).read_text(encoding="utf-8"))
        if report["schema"] != SCHEMA:
            raise AssertionError("wrong feature-only Burns output schema")
        if report["counts"]["exact_lexical_occurrences"] != 3:
            raise AssertionError("feature-only Burns writer lost exact occurrences")
        if report["counts"]["max_lane"] < 2:
            raise AssertionError("same-start overlap did not require distinct lanes")
        inventory = {item.name for item in directory.iterdir()}
        if {"otype.tf", "oslots.tf", "otext.tf"} & inventory:
            raise AssertionError("feature-only Burns module emitted a warp/config replacement")

        base_info = corpus_manager.load(str(cuc), name="reviewed-cuc-feature-base")
        combined_info = corpus_manager.load(
            [str(cuc), str(directory)], name="reviewed-cuc-with-burns-feature-module"
        )
        _, api = corpus_manager.get("reviewed-cuc-with-burns-feature-module")
        if base_info.max_slot != combined_info.max_slot or combined_info.max_slot != old_slots:
            raise AssertionError("Burns module changed CUC sign slots")
        if base_info.max_node != combined_info.max_node or combined_info.max_node != old_max:
            raise AssertionError("Burns module changed CUC node universe")
        if tuple(api.F.otype.s("entity")):
            raise AssertionError("feature-only Burns module created entity nodes")
        if tuple(api.E.oslots.s(word)) != old_word_slots:
            raise AssertionError("Burns module changed CUC word extent")

        categories = {
            api.Fs(f"burns_category_{lane}", warn=False).v(word)
            for lane in range(1, int(report["counts"]["max_lane"]) + 1)
            if api.Fs(f"burns_category_{lane}", warn=False)
            and api.Fs(f"burns_category_{lane}", warn=False).v(word)
        }
        if categories != {"divine_name", "cultic_action"}:
            raise AssertionError(f"same-word Burns categories lost across lanes: {categories!r}")

        roots = {
            api.Fs(f"burns_root_{lane}", warn=False).v(word)
            for lane in range(1, int(report["counts"]["max_lane"]) + 1)
            if api.Fs(f"burns_root_{lane}", warn=False)
            and api.Fs(f"burns_root_{lane}", warn=False).v(word)
        }
        if roots != {"SYNROOT"}:
            raise AssertionError(f"cultic-action root lost from lane metadata: {roots!r}")

        phrase_alignment = next(
            alignment
            for alignment, annotation in zip(alignments, source.annotations, strict=True)
            if annotation.headword == phrase_label
        )
        phrase_occurrence = phrase_alignment.occurrences[0]
        if tuple(phrase_occurrence.anchor_nodes) != phrase_words:
            raise AssertionError("synthetic phrase did not align to chosen CUC words")
        lane_item = next(
            item
            for item in report["occurrence_lanes"]
            if tuple(item["span_nodes"]) == phrase_words
        )
        phrase_lane = int(lane_item["lane"])
        span_edge = api.Es(f"burns_span_{phrase_lane}", warn=False)
        if not span_edge or tuple(span_edge.f(phrase_words[0])) != phrase_words[1:]:
            raise AssertionError("feature-only span edge lost multiword membership")

        if api.F.burns_locus.v(tablet_node) != "SYN":
            raise AssertionError("findspot was not scoped to existing CUC tablet")
        if api.F.burns_locus.v(word) is not None:
            raise AssertionError("tablet findspot leaked onto word")

        divine_nodes: set[int] = set()
        action_nodes: set[int] = set()
        for lane in range(1, int(report["counts"]["max_lane"]) + 1):
            for category, target in (
                ("divine_name", divine_nodes),
                ("cultic_action", action_nodes),
            ):
                response = tools.search(
                    f"word burns_category_{lane}={category}",
                    corpus="reviewed-cuc-with-burns-feature-module",
                    limit=20,
                )
                if "error" not in response:
                    target.update(_returned_nodes(response))
        if divine_nodes != {word} or action_nodes != {word}:
            raise AssertionError(
                f"cfabric-mcp lost same-word lane queries: divine={divine_nodes!r}, action={action_nodes!r}"
            )

        phrase_response = tools.search(
            f"s:word burns_category_{phrase_lane}=cultic_jargon\n"
            "m:word\n"
            f"s -burns_span_{phrase_lane}> m",
            corpus="reviewed-cuc-with-burns-feature-module",
            limit=20,
        )
        if "error" in phrase_response:
            raise AssertionError(f"cfabric-mcp rejected Burns span-edge search: {phrase_response!r}")
        returned = _returned_nodes(phrase_response)
        if not set(phrase_words).issubset(returned):
            raise AssertionError(
                f"cfabric-mcp span query lost phrase members: {returned!r}"
            )

    print(
        "Reviewed CUC + primary feature-only Burns module + overlapping lanes + "
        "multiword span edge + tablet findspot + MCP search: PASS"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cuc_dir", type=Path)
    args = parser.parse_args()
    run(args.cuc_dir)


if __name__ == "__main__":
    main()
