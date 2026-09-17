from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from tf.fabric import Fabric

from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cuc_index import CucCompatibility, ReviewedCucIndex
from ugarit_context_parsing.module import (
    BurnsModuleData,
    build_burns_module,
    build_burns_module_report,
    burns_node_annotations,
    write_burns_module,
)
from ugarit_context_parsing.source import WorkbookRecord


EXPECTED_FEATURES = {
    "burns_annotations",
    "burns_annotation_ids",
    "burns_semantic_statuses",
    "burns_worksheet_roles",
    "burns_sections",
    "burns_headwords",
}
EXPECTED_FILES = {f"{name}.tf" for name in EXPECTED_FEATURES}
REPORT_FILE = "burns-module-report.json"


def _record(
    row: int,
    *,
    headword: str,
    references: str,
    section: str = "Section α",
    root: str = "",
    comments: str = "",
    point: str = "",
    depth: str = "",
    disputed: str = "",
) -> WorkbookRecord:
    return WorkbookRecord(
        source_file="01 Synthetic/Worksheet 1.csv",
        source_row=row,
        source_page=6 + row,
        section=section,
        root=root,
        headword=headword,
        ktu="1.14",
        references=references,
        locus="GP",
        room=f"R{row}",
        point=point,
        depth=depth,
        disputed=disputed,
        comments=comments,
    )


def _source():
    return normalize_workbook_records(
        (
            _record(
                1,
                headword="bʿl",
                references="I.2",
                comments="synthetic α; quoted \"note\"\nsecond line",
                point="p:α",
                depth="d\n2",
                disputed="?",
            ),
            # Distinct annotation identity, same exact lexical CUC word after
            # the documented matching-only editorial suffix is stripped.
            _record(2, headword="bʿl*", references="I.2"),
            _record(3, headword="bʿl mlk", references="I.3"),
            _record(4, headword="mlk x", references="I.3"),
            _record(5, headword="mlk", references="I.3"),
        )
    )


def _compatibility() -> CucCompatibility:
    return CucCompatibility(
        repository="DT-UCPH/cuc",
        commit="ad69400f5446e1c8217af01659c7c10ab00c015b",
        version="0.2.8",
        manifest_sha256="717e5b7f1c60b800e05f50f4cac27dac7562b45eecb48a8686c64cfab42a92ba",
        files=(),
    )


def _index(*, compatibility: CucCompatibility | None = None) -> ReviewedCucIndex:
    return ReviewedCucIndex(
        compatibility=_compatibility() if compatibility is None else compatibility,
        tablet_nodes=MappingProxyType({"KTU 1.14": 16}),
        column_nodes=MappingProxyType({("KTU 1.14", "I"): 15}),
        line_nodes=MappingProxyType(
            {
                ("KTU 1.14", "I", 2): 13,
                ("KTU 1.14", "I", 3): 14,
            }
        ),
        bare_line_candidates=MappingProxyType(
            {
                ("KTU 1.14", 2): (13,),
                ("KTU 1.14", 3): (14,),
            }
        ),
        line_words=MappingProxyType(
            {
                13: (7, 8, 9),
                14: (10, 11, 12),
            }
        ),
        word_g_cons=MappingProxyType(
            {
                7: "w",
                8: "bʿl",
                9: "x",
                10: "bʿl",
                11: "mlk",
                12: "x",
            }
        ),
        word_slots=MappingProxyType(
            {
                7: (1,),
                8: (2,),
                9: (3,),
                10: (4,),
                11: (5,),
                12: (6,),
            }
        ),
    )


def _module_fixture():
    source = _source()
    index = _index()
    alignments = align_burns_source(source, index)
    module = build_burns_module(source, alignments, index)
    report = build_burns_module_report(source, alignments, index, module)
    return source, index, alignments, module, report


def _write_synthetic_base(path: Path) -> None:
    otype = {
        **{node: "sign" for node in range(1, 7)},
        **{node: "word" for node in range(7, 13)},
        13: "line",
        14: "line",
        15: "column",
        16: "tablet",
    }
    oslots = {
        7: {1},
        8: {2},
        9: {3},
        10: {4},
        11: {5},
        12: {6},
        13: {1, 2, 3},
        14: {4, 5, 6},
        15: {1, 2, 3, 4, 5, 6},
        16: {1, 2, 3, 4, 5, 6},
    }
    fabric = Fabric(locations=[], modules=[], silent="deep")
    self_ok = fabric.save(
        nodeFeatures={"otype": otype},
        edgeFeatures={"oslots": oslots},
        metaData={
            "otype": {"valueType": "str", "description": "synthetic node type"},
            "oslots": {"valueType": "int", "description": "synthetic warp"},
            "otext": {"sectionTypes": "", "sectionFeatures": ""},
        },
        location=str(path),
        module="",
        silent="deep",
    )
    if not self_ok:
        raise AssertionError("failed to build synthetic TF base")


class _FailingFabric:
    def __init__(self, **kwargs):
        pass

    def save(self, **kwargs):
        return False


class _UnexpectedFileFabric:
    def __init__(self, **kwargs):
        pass

    def save(self, **kwargs):
        location = Path(kwargs["location"])
        location.mkdir(parents=True, exist_ok=True)
        for name in EXPECTED_FILES:
            (location / name).write_text("synthetic\n", encoding="utf-8")
        (location / "otype.tf").write_text("forbidden\n", encoding="utf-8")
        return True


class BurnsTfModuleTests(unittest.TestCase):
    def test_two_annotations_on_one_node_are_lossless(self):
        source, _, _, module, _ = _module_fixture()
        payloads = burns_node_annotations(module.node_features["burns_annotations"][8])
        self.assertEqual(len(payloads), 2)
        self.assertEqual(
            {item["annotation_id"] for item in payloads},
            {source.annotations[0].annotation_id, source.annotations[1].annotation_id},
        )
        self.assertEqual(len({item["occurrence_id"] for item in payloads}), 2)

    def test_multiword_span_is_reconstructable_from_every_participating_word(self):
        source, _, _, module, _ = _module_fixture()
        annotation_id = source.annotations[2].annotation_id
        copies = []
        for node in (10, 11):
            payloads = burns_node_annotations(module.node_features["burns_annotations"][node])
            matches = [item for item in payloads if item["annotation_id"] == annotation_id]
            self.assertEqual(len(matches), 1)
            copies.append(matches[0])
        self.assertEqual(copies[0], copies[1])
        self.assertEqual(copies[0]["anchor_kind"], "word_span")
        self.assertEqual(copies[0]["anchor_nodes"], [10, 11])
        self.assertEqual(len({copies[0]["occurrence_id"], copies[1]["occurrence_id"]}), 1)

    def test_nested_and_overlapping_spans_coexist(self):
        source, _, _, module, _ = _module_fixture()
        payloads = burns_node_annotations(module.node_features["burns_annotations"][11])
        by_annotation = {item["annotation_id"]: item for item in payloads}
        expected = {
            source.annotations[2].annotation_id: [10, 11],
            source.annotations[3].annotation_id: [11, 12],
            source.annotations[4].annotation_id: [11],
        }
        self.assertEqual(
            {annotation_id: by_annotation[annotation_id]["anchor_nodes"] for annotation_id in expected},
            expected,
        )

    def test_repeated_build_is_deterministic_and_does_not_duplicate_span_copies(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)
        first = build_burns_module(source, alignments, index)
        second = build_burns_module(source, alignments, index)
        reversed_input = build_burns_module(source, tuple(reversed(alignments)), index)
        self.assertEqual(dict(first.node_features), dict(second.node_features))
        self.assertEqual(dict(first.node_features), dict(reversed_input.node_features))

        payloads = burns_node_annotations(first.node_features["burns_annotations"][10])
        occurrence_ids = [item["occurrence_id"] for item in payloads]
        self.assertEqual(len(occurrence_ids), len(set(occurrence_ids)))

    def test_row_level_unicode_newlines_punctuation_and_ordered_provenance_survive_payload(self):
        source, _, _, module, _ = _module_fixture()
        payload = next(
            item
            for item in burns_node_annotations(module.node_features["burns_annotations"][8])
            if item["annotation_id"] == source.annotations[0].annotation_id
        )
        self.assertEqual(payload["record_ids"], list(source.annotations[0].record_ids))
        self.assertEqual(len(payload["source_records"]), 1)
        row = payload["source_records"][0]
        self.assertEqual(row["record_id"], source.records[0].record_id)
        self.assertEqual(row["source_file"], "01 Synthetic/Worksheet 1.csv")
        self.assertEqual(row["source_row"], 1)
        self.assertEqual(row["source_page"], 7)
        self.assertEqual(row["point"], "p:α")
        self.assertEqual(row["depth"], "d\n2")
        self.assertEqual(row["disputed"], "?")
        self.assertEqual(row["comments"], 'synthetic α; quoted "note"\nsecond line')

    def test_projections_are_exactly_derived_from_authoritative_payload(self):
        _, _, _, module, _ = _module_fixture()
        for node, authoritative in module.node_features["burns_annotations"].items():
            payloads = burns_node_annotations(authoritative)
            expected = {
                "burns_annotation_ids": sorted({str(item["annotation_id"]) for item in payloads}),
                "burns_semantic_statuses": sorted({str(item["semantic_status"]) for item in payloads}),
                "burns_worksheet_roles": sorted({str(item["worksheet_role"]) for item in payloads}),
                "burns_sections": sorted({str(item["section"]) for item in payloads}),
                "burns_headwords": sorted({str(item["headword"]) for item in payloads}),
            }
            for feature, values in expected.items():
                self.assertEqual(json.loads(module.node_features[feature][node]), values)

    def test_exact_reviewed_cuc_identity_is_on_every_feature(self):
        _, _, _, module, _ = _module_fixture()
        self.assertEqual(set(module.node_features), EXPECTED_FEATURES)
        self.assertEqual(set(module.metadata), EXPECTED_FEATURES)
        for feature in EXPECTED_FEATURES:
            metadata = module.metadata[feature]
            self.assertEqual(metadata["valueType"], "str")
            self.assertEqual(metadata["module"], "Burns")
            self.assertEqual(metadata["moduleSchema"], "burns-tf-module-v1")
            self.assertEqual(metadata["cucRepository"], "DT-UCPH/cuc")
            self.assertEqual(metadata["cucCommit"], "ad69400f5446e1c8217af01659c7c10ab00c015b")
            self.assertEqual(metadata["cucVersion"], "0.2.8")
            self.assertEqual(
                metadata["cucManifestSha256"],
                "717e5b7f1c60b800e05f50f4cac27dac7562b45eecb48a8686c64cfab42a92ba",
            )

    def test_missing_or_mismatched_cuc_compatibility_fails_closed(self):
        source = _source()
        unbound = _index(compatibility=None)
        # `_index()` uses the reviewed identity by default, so explicitly replace it.
        unbound = replace(unbound, compatibility=None)
        with self.assertRaises(ValueError):
            build_burns_module(source, align_burns_source(source, unbound), unbound)

        mismatched = _index(
            compatibility=replace(_compatibility(), commit="not-the-reviewed-cuc")
        )
        with self.assertRaises(ValueError):
            build_burns_module(source, align_burns_source(source, mismatched), mismatched)

    def test_forged_alignment_or_module_cannot_be_reported_as_authoritative(self):
        source, index, alignments, module, _ = _module_fixture()
        forged_occurrence = replace(alignments[0].occurrences[0], anchor_nodes=(999,))
        forged_alignment = replace(alignments[0], occurrences=(forged_occurrence,))
        with self.assertRaises(ValueError):
            build_burns_module(source, (forged_alignment, *alignments[1:]), index)

        changed_features = {name: dict(values) for name, values in module.node_features.items()}
        changed_features["burns_headwords"][8] = json.dumps(["forged"])
        forged_module = BurnsModuleData(
            node_features=changed_features,
            metadata={name: dict(values) for name, values in module.metadata.items()},
        )
        with self.assertRaises(ValueError):
            build_burns_module_report(source, alignments, index, forged_module)

    def test_report_accounts_for_unanchored_and_selected_results(self):
        source, index, alignments, module, report = _module_fixture()
        self.assertEqual(report["schema"], "burns-tf-module-report-v1")
        self.assertEqual(report["counts"]["records"], len(source.records))
        self.assertEqual(report["counts"]["annotations"], len(source.annotations))
        self.assertEqual(report["counts"]["selected_occurrences"], 5)
        self.assertEqual(report["counts"]["touched_nodes"], len(module.node_features["burns_annotations"]))
        self.assertEqual(report["feature_inventory"], sorted(EXPECTED_FEATURES))
        self.assertEqual(report["alignment"]["schema"], "burns-cuc-alignment-report-v1")
        self.assertEqual(report["cuc_compatibility"]["commit"], index.compatibility.commit)

    def test_real_tf_save_and_combined_reload_preserve_payload_and_do_not_emit_warp(self):
        source, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base"
            output = root / "burns-module"
            _write_synthetic_base(base)
            self.assertTrue(write_burns_module(module, report, output))

            self.assertEqual(
                {path.name for path in output.iterdir() if path.is_file()},
                EXPECTED_FILES | {REPORT_FILE},
            )
            for forbidden in (
                "otype.tf",
                "oslots.tf",
                "otext.tf",
                "g_cons.tf",
                "tablet.tf",
                "column.tf",
                "line.tf",
            ):
                self.assertFalse((output / forbidden).exists(), forbidden)

            api = Fabric(
                locations=[str(base), str(output)],
                modules=[""],
                silent="deep",
            ).loadAll(silent="deep")
            self.assertIsNotNone(api)
            assert api is not None
            self.assertEqual(api.F.otype.maxSlot, 6)
            self.assertEqual(api.F.otype.maxNode, 16)
            self.assertEqual(tuple(api.F.otype.s("word")), (7, 8, 9, 10, 11, 12))
            payloads = burns_node_annotations(api.F.burns_annotations.v(8))
            first = next(
                item
                for item in payloads
                if item["annotation_id"] == source.annotations[0].annotation_id
            )
            self.assertEqual(first["source_records"][0]["comments"], 'synthetic α; quoted "note"\nsecond line')
            self.assertEqual(first["source_records"][0]["depth"], "d\n2")

    def test_failed_tf_save_leaves_previous_module_untouched(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            output.mkdir()
            old = output / "burns_annotations.tf"
            old.write_text("old-authoritative\n", encoding="utf-8")
            old_report = output / REPORT_FILE
            old_report.write_text('{"old":true}\n', encoding="utf-8")

            self.assertFalse(
                write_burns_module(
                    module,
                    report,
                    output,
                    fabric_factory=_FailingFabric,
                )
            )
            self.assertEqual(old.read_text(encoding="utf-8"), "old-authoritative\n")
            self.assertEqual(old_report.read_text(encoding="utf-8"), '{"old":true}\n')

    def test_unexpected_staged_tf_file_is_rejected_without_touching_previous_output(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            output.mkdir()
            sentinel = output / "burns_annotations.tf"
            sentinel.write_text("old\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                write_burns_module(
                    module,
                    report,
                    output,
                    fabric_factory=_UnexpectedFileFabric,
                )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "old\n")
            self.assertFalse((output / "otype.tf").exists())

    def test_successful_replacement_removes_stale_burns_tf_file(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            output.mkdir()
            (output / "burns_obsolete_projection.tf").write_text("stale\n", encoding="utf-8")
            (output / REPORT_FILE).write_text('{"old":true}\n', encoding="utf-8")
            self.assertTrue(write_burns_module(module, report, output))
            self.assertFalse((output / "burns_obsolete_projection.tf").exists())
            self.assertEqual(
                {path.name for path in output.iterdir() if path.is_file()},
                EXPECTED_FILES | {REPORT_FILE},
            )

    def test_mid_publication_failure_rolls_back_previous_complete_module(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            output.mkdir()
            previous = {
                "burns_annotations.tf": "old-authoritative\n",
                "burns_headwords.tf": "old-headwords\n",
                REPORT_FILE: '{"old":true}\n',
            }
            for name, content in previous.items():
                (output / name).write_text(content, encoding="utf-8")

            original_replace = Path.replace
            install_count = 0

            def flaky_replace(path: Path, target):
                nonlocal install_count
                target_path = Path(target)
                # Backup moves target the hidden backup directory. Fail only
                # during the second stage->output installation move.
                if path.parent != output and target_path.parent == output:
                    install_count += 1
                    if install_count == 2:
                        raise OSError("synthetic mid-publication failure")
                return original_replace(path, target)

            with patch.object(Path, "replace", flaky_replace):
                with self.assertRaises(OSError):
                    write_burns_module(module, report, output)

            self.assertEqual(
                {name: (output / name).read_text(encoding="utf-8") for name in previous},
                previous,
            )
            self.assertEqual(
                {path.name for path in output.iterdir() if path.is_file()},
                set(previous),
            )


if __name__ == "__main__":
    unittest.main()
