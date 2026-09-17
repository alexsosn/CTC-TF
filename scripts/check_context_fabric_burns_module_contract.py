#!/usr/bin/env python3
"""Real Context-Fabric/cfabric-mcp compatibility contract for CUC + v1 Burns.

The production `module` entry point emits v2 native entities. This distinct
contract intentionally pins the explicit `module-v1` compatibility command to
prove that existing consumers retain their historical feature-only behavior.
"""

from __future__ import annotations

import argparse
import csv
import tempfile
from collections import Counter
from pathlib import Path

from ugarit_context_parsing.alignment import BurnsAnchorKind, align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cli import main as cli_main
from ugarit_context_parsing.cuc_index import build_reviewed_cuc_index
from ugarit_context_parsing.module import FEATURES, REPORT_FILE, burns_node_annotations
from ugarit_context_parsing.source import WORKBOOK_FIELDS, WorkbookRecord


def _choose_unique_word(index):
    """Pick one public CUC word that resolves uniquely inside its exact line."""
    for (tablet, column, line), line_node in sorted(index.line_nodes.items()):
        words = index.line_words[line_node]
        values = tuple(index.word_g_cons[word] for word in words)
        counts = Counter(values)
        for word, value in zip(words, values, strict=True):
            if not value or any(character.isspace() for character in value):
                continue
            if value.endswith(("*", "†", "!", "?")):
                continue
            if counts[value] != 1:
                continue
            return tablet, column, line, line_node, word, value
    raise AssertionError("reviewed CUC has no suitable unique synthetic-contract word")


def _synthetic_record(*, tablet: str, column: str, line: int, headword: str) -> WorkbookRecord:
    if not tablet.startswith("KTU "):
        raise AssertionError(f"unexpected reviewed CUC tablet label: {tablet!r}")
    return WorkbookRecord(
        source_file="01 Synthetic/Worksheet 1.csv",
        source_row=1,
        source_page=1,
        section="Section synthetic",
        root="",
        headword=headword,
        ktu=tablet.removeprefix("KTU "),
        references=f"{column}.{line}",
        locus="SYN",
        room="1",
        point="p1",
        depth="synthetic",
        disputed="",
        comments="synthetic Context-Fabric v1 compatibility contract",
    )


def _write_synthetic_csv(root: Path, record: WorkbookRecord) -> None:
    path = root / record.source_file
    path.parent.mkdir(parents=True)
    row = {field: str(getattr(record, field)) for field in WORKBOOK_FIELDS}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WORKBOOK_FIELDS)
        writer.writeheader()
        writer.writerow(row)


def _type_counts(info) -> dict[str, int]:
    return {item["type"]: int(item["count"]) for item in info.node_types}


def _assert_feature_only_inventory(output: Path) -> None:
    expected = {f"{feature}.tf" for feature in FEATURES} | {REPORT_FILE}
    actual = {path.name for path in output.iterdir() if path.is_file()}
    if actual != expected:
        raise AssertionError(
            f"Burns v1 inventory differs: expected {sorted(expected)!r}, got {sorted(actual)!r}"
        )
    forbidden = {"otype.tf", "oslots.tf", "otext.tf", "g_cons.tf", "tablet.tf", "column.tf", "line.tf"}
    leaked = sorted(forbidden & actual)
    if leaked:
        raise AssertionError("Burns v1 copied CUC-owned features: " + ", ".join(leaked))


def run_contract(cuc_dir: str | Path) -> None:
    from cfabric_mcp import tools
    from cfabric_mcp.corpus_manager import corpus_manager

    cuc = Path(cuc_dir).resolve()
    index = build_reviewed_cuc_index(cuc)
    tablet, column, line, line_node, word_node, headword = _choose_unique_word(index)
    record = _synthetic_record(tablet=tablet, column=column, line=line, headword=headword)
    expected_source = normalize_workbook_records((record,))
    expected_alignments = align_burns_source(expected_source, index)
    if len(expected_alignments) != 1 or len(expected_alignments[0].occurrences) != 1:
        raise AssertionError("synthetic Burns source did not produce exactly one occurrence")
    occurrence = expected_alignments[0].occurrences[0]
    if occurrence.anchor_kind is not BurnsAnchorKind.WORD_SPAN:
        raise AssertionError(f"expected unique word-span anchor, got {occurrence.anchor_kind!r}")
    if occurrence.anchor_nodes != (word_node,):
        raise AssertionError(
            f"alignment selected {occurrence.anchor_nodes!r}, expected public CUC word {(word_node,)!r}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        source_root = tmp_root / "burns-source"
        output = tmp_root / "burns-module-v1"
        _write_synthetic_csv(source_root, record)

        # Preserve the prior v1 contract only via the explicitly named
        # compatibility entry point. The separate native-CUC workflow verifies
        # the primary `module` command and its extended warp.
        result = cli_main([
            "module-v1", str(source_root), "--input-format", "csv",
            "--cuc", str(cuc), "--output", str(output),
        ])
        if result != 0:
            raise AssertionError(f"public Burns module-v1 CLI returned {result!r}")
        _assert_feature_only_inventory(output)

        base_info = corpus_manager.load(str(cuc), name="cuc-base")
        base_api = corpus_manager.get_api("cuc-base")
        base_type_vector = tuple(
            base_api.F.otype.v(node) for node in range(1, base_info.max_node + 1)
        )
        base_line_words = tuple(base_api.L.d(line_node, otype="word"))

        composed_info = corpus_manager.load([str(cuc), str(output)], name="cuc-with-burns-v1")
        composed_cf, composed_api = corpus_manager.get("cuc-with-burns-v1")
        if tuple(Path(path).resolve() for path in composed_cf.locations) != (cuc, output.resolve()):
            raise AssertionError(f"consumer did not preserve ordered locations: {composed_cf.locations!r}")
        if composed_info.max_slot != base_info.max_slot:
            raise AssertionError("Burns v1 changed the CUC maximum slot")
        if composed_info.max_node != base_info.max_node:
            raise AssertionError("Burns v1 changed the CUC maximum node")
        if _type_counts(composed_info) != _type_counts(base_info):
            raise AssertionError("Burns v1 changed CUC node-type counts")
        if tuple(
            composed_api.F.otype.v(node) for node in range(1, composed_info.max_node + 1)
        ) != base_type_vector:
            raise AssertionError("Burns v1 changed the CUC node-type vector")
        if tuple(composed_api.L.d(line_node, otype="word")) != base_line_words:
            raise AssertionError("Burns v1 changed CUC line navigation")

        missing = sorted(set(FEATURES) - set(composed_info.node_features))
        if missing:
            raise AssertionError("cfabric-mcp omitted Burns v1 features: " + ", ".join(missing))
        raw = composed_api.Fs("burns_annotations", warn=False).v(word_node)
        if not raw:
            raise AssertionError("composed v1 API cannot access selected CUC word annotations")
        payloads = burns_node_annotations(raw)
        if (
            len(payloads) != 1
            or payloads[0]["annotation_id"] != expected_source.annotations[0].annotation_id
        ):
            raise AssertionError("composed Burns v1 payload does not match synthetic source")
        if payloads[0]["anchor_nodes"] != [word_node]:
            raise AssertionError("composed Burns v1 payload lost exact CUC word anchor")

        search_result = tools.search(
            "word burns_annotations~burns-node-annotation-v1",
            corpus="cuc-with-burns-v1", limit=20,
        )
        if "error" in search_result:
            raise AssertionError(f"MCP Burns v1 feature search failed: {search_result!r}")
        returned_nodes = {
            int(node["node"])
            for row in search_result.get("results", [])
            for node in row
        }
        if word_node not in returned_nodes:
            raise AssertionError(
                f"MCP Burns v1 search missed selected CUC word {word_node}: {search_result!r}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cuc_dir", help="Exact reviewed CUC Text-Fabric directory")
    args = parser.parse_args()
    run_contract(args.cuc_dir)


if __name__ == "__main__":
    main()
