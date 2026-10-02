from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tf.fabric import Fabric

from test_burns_tf_module import _index, _record, _source, _write_synthetic_base
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.feature_module import (
    REPORT_FILE,
    SCHEMA,
    build_feature_module,
    build_feature_module_report,
    write_feature_module,
)




class _RefuseFabric:
    def __init__(self, **kwargs):
        pass

    def save(self, **kwargs):
        return False


class _ExtraDirectoryFabric:
    def __init__(self, **kwargs):
        self._fabric = Fabric(**kwargs)

    def save(self, **kwargs):
        saved = self._fabric.save(**kwargs)
        if saved:
            (Path(kwargs["location"]) / "foreign-directory").mkdir()
        return saved


def _fixture():
    source = _source()
    index = _index()
    alignments = align_burns_source(source, index)
    module = build_feature_module(source, alignments, index)
    report = build_feature_module_report(source, alignments, index, module)
    return source, index, alignments, module, report


def _lane(module, start: int, lane: int) -> tuple[str, int, tuple[int, ...]]:
    occurrence = module.node_features[f"burns_occurrence_id_{lane}"][start]
    length = int(module.node_features[f"burns_span_length_{lane}"][start])
    edge = module.edge_features.get(f"burns_span_{lane}", {})
    return occurrence, length, (start, *tuple(sorted(edge.get(start, set()))))


class FeatureOnlyModuleBuildTests(unittest.TestCase):
    def test_exact_occurrences_use_existing_word_carriers_and_dynamic_lanes(self):
        source, index, _, module, report = _fixture()

        self.assertEqual(module.max_lane, 2)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["counts"]["exact_lexical_occurrences"], 5)
        self.assertEqual(report["counts"]["max_lane"], 2)

        self.assertEqual(
            {
                module.node_features["burns_headword_1"][8],
                module.node_features["burns_headword_2"][8],
            },
            {"bʿl", "bʿl*"},
        )
        self.assertEqual(
            {
                module.node_features["burns_headword_1"][11],
                module.node_features["burns_headword_2"][11],
            },
            {"mlk", "mlk x"},
        )

        word_nodes = set(index.word_g_cons)
        all_base_nodes = (
            word_nodes
            | set(index.line_nodes.values())
            | set(index.column_nodes.values())
            | set(index.tablet_nodes.values())
        )
        for name, values in module.node_features.items():
            self.assertTrue(set(values).issubset(all_base_nodes), name)
            if name.startswith("burns_") and name not in {
                "burns_locus", "burns_room", "burns_point", "burns_depth", "burns_disputed"
            }:
                self.assertTrue(set(values).issubset(word_nodes), name)
        for name, values in module.edge_features.items():
            self.assertTrue(name.startswith("burns_span_"))
            self.assertTrue(set(values).issubset(word_nodes))
            self.assertTrue(
                all(set(targets).issubset(word_nodes) for targets in values.values())
            )

        self.assertEqual(module.node_features["burns_locus"], {16: "GP"})

    def test_multiword_and_identical_spans_are_reconstructable_without_new_nodes(self):
        _, _, _, module, _ = _fixture()

        # bʿl mlk starts at 10 and must reconstruct to words 10,11.
        b_lanes = [
            lane
            for lane in range(1, module.max_lane + 1)
            if module.node_features.get(f"burns_headword_{lane}", {}).get(10) == "bʿl mlk"
        ]
        self.assertEqual(b_lanes, [1])
        _, length, span = _lane(module, 10, b_lanes[0])
        self.assertEqual(length, 2)
        self.assertEqual(span, (10, 11))

        # Same-start independent one-word bʿl / bʿl* occurrences stay distinct.
        occurrences = {
            _lane(module, 8, lane)[0]
            for lane in (1, 2)
        }
        self.assertEqual(len(occurrences), 2)
        for lane in (1, 2):
            _, length, span = _lane(module, 8, lane)
            self.assertEqual((length, span), (1, (8,)))

        # Same start, distinct nested spans at word 11 are independent lanes.
        spans = {_lane(module, 11, lane)[2] for lane in (1, 2)}
        self.assertEqual(spans, {(11,), (11, 12)})

    def test_non_exact_structural_fallback_is_report_only(self):
        source = normalize_workbook_records(
            (
                _record(1, headword="not-in-line", references="I.2"),
            )
        )
        index = _index()
        alignments = align_burns_source(source, index)
        module = build_feature_module(source, alignments, index)

        lexical_names = [
            name
            for name in module.node_features
            if name.startswith(("burns_occurrence_id_", "burns_annotation_id_", "burns_headword_",
                                "burns_match_rule_", "burns_root_", "burns_category_", "burns_semantic_status_",
                                "burns_worksheet_role_", "burns_section_", "burns_span_length_"))
        ]
        self.assertEqual(lexical_names, [])
        self.assertEqual(module.edge_features, {})
        self.assertEqual(module.max_lane, 0)


    def test_findspot_conflicts_remain_audit_only_and_tablet_scope_is_native(self):
        _, _, _, module, _ = _fixture()
        self.assertEqual(module.node_features["burns_locus"], {16: "GP"})
        self.assertNotIn("burns_room", module.node_features)
        self.assertEqual(
            module.findspot_audit.conflicts[16]["burns_room"],
            ("R1", "R2", "R3", "R4", "R5"),
        )
        self.assertIn("burns_point", module.findspot_audit.incomplete[16])

    def test_nonliteral_exact_candidates_publish_match_rule_per_lane(self):
        source = normalize_workbook_records((
            _record(1, headword="bʿl (x)", references="I.2"),
            _record(2, headword="bʿl/foo", references="I.2"),
        ))
        index = _index()
        module = build_feature_module(source, align_burns_source(source, index), index)

        rules = {
            module.node_features[f"burns_match_rule_{lane}"][8]
            for lane in range(1, module.max_lane + 1)
        }
        self.assertEqual(rules, {"parenthesis_core", "slash_left"})
        self.assertEqual(
            {
                module.node_features[f"burns_headword_{lane}"][8]
                for lane in range(1, module.max_lane + 1)
            },
            {"bʿl (x)", "bʿl/foo"},
        )

    def test_root_category_and_negative_status_remain_distinct_across_lanes(self):
        source = normalize_workbook_records((
            replace(
                _record(1, headword="mlk", references="I.3", section="Section α1", root="MLK"),
                source_file="09 Synthetic/Worksheet 1.csv",
            ),
            replace(
                _record(2, headword="mlk", references="I.3", section="Section β"),
                source_file="02 Synthetic/Worksheet 1.csv",
            ),
        ))
        index = _index()
        module = build_feature_module(source, align_burns_source(source, index), index)

        carriers = {
            lane: module.node_features[f"burns_category_{lane}"][11]
            for lane in range(1, module.max_lane + 1)
        }
        self.assertEqual(set(carriers.values()), {"cultic_action", "personal_name"})
        action_lane = next(lane for lane, category in carriers.items() if category == "cultic_action")
        name_lane = next(lane for lane, category in carriers.items() if category == "personal_name")
        self.assertEqual(module.node_features[f"burns_root_{action_lane}"][11], "MLK")
        self.assertNotIn(11, module.node_features.get(f"burns_root_{name_lane}", {}))
        self.assertEqual(
            module.node_features[f"burns_semantic_status_{name_lane}"][11],
            "homograph_excluded",
        )
        self.assertNotIn("burns_lemma_1", module.node_features)

    def test_build_is_deterministic_under_reversed_alignment_input(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)
        first = build_feature_module(source, alignments, index)
        second = build_feature_module(source, tuple(reversed(alignments)), index)
        self.assertEqual(dict(first.node_features), dict(second.node_features))
        self.assertEqual(dict(first.edge_features), dict(second.edge_features))
        self.assertEqual(dict(first.metadata), dict(second.metadata))
        self.assertEqual(first.max_lane, second.max_lane)


class FeatureOnlyModuleWriterTests(unittest.TestCase):
    def test_writer_emits_only_weft_features_and_combined_warp_is_identical(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            output = root / "burns"
            _write_synthetic_base(base)

            self.assertTrue(write_feature_module(module, report, output))
            inventory = {item.name for item in output.iterdir()}
            self.assertIn(REPORT_FILE, inventory)
            self.assertFalse({"otype.tf", "oslots.tf", "otext.tf"} & inventory)
            self.assertFalse({
                "burns_annotations.tf", "burns_annotation_ids.tf",
                "burns_headwords.tf", "burns_semantic_statuses.tf",
                "burns_worksheet_roles.tf", "burns_sections.tf",
            } & inventory)

            base_api = Fabric(
                locations=[str(base)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            combined = Fabric(
                locations=[str(base), str(output)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            self.assertIsNotNone(base_api)
            self.assertIsNotNone(combined)
            assert base_api is not None and combined is not None

            self.assertEqual(combined.F.otype.maxSlot, base_api.F.otype.maxSlot)
            self.assertEqual(combined.F.otype.maxNode, base_api.F.otype.maxNode)
            for node in range(1, base_api.F.otype.maxNode + 1):
                self.assertEqual(combined.F.otype.v(node), base_api.F.otype.v(node))
                if node > base_api.F.otype.maxSlot:
                    self.assertEqual(
                        tuple(combined.E.oslots.s(node)),
                        tuple(base_api.E.oslots.s(node)),
                    )

            hits = tuple(combined.S.search(
                "s:word burns_category_1=divine_name\n"
                "m:word\n"
                "s -burns_span_1> m",
                silent="deep",
            ))
            self.assertEqual(hits, ((10, 11),))

            oneword = tuple(combined.S.search(
                "s:word burns_span_length_1=1",
                silent="deep",
            ))
            self.assertTrue(any(row[0] == 8 for row in oneword))

            payload = json.loads((output / REPORT_FILE).read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], SCHEMA)
            self.assertEqual(payload["counts"]["exact_lexical_occurrences"], 5)


    def test_writer_rejects_forged_report_identity_and_counts_before_fabric(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            forged_identity = json.loads(json.dumps(report))
            forged_identity["cuc_compatibility"]["commit"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "compatibility|fingerprint|CUC"):
                write_feature_module(
                    module,
                    forged_identity,
                    root / "identity",
                    fabric_factory=_RefuseFabric,
                )
            self.assertFalse((root / "identity").exists())

            forged_counts = json.loads(json.dumps(report))
            forged_counts["counts"]["exact_lexical_occurrences"] += 1
            with self.assertRaisesRegex(ValueError, "count|occurrence|report"):
                write_feature_module(
                    module,
                    forged_counts,
                    root / "counts",
                    fabric_factory=_RefuseFabric,
                )
            self.assertFalse((root / "counts").exists())

    def test_writer_rejects_forged_occurrence_lanes_and_findspot_audit(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            forged_lanes = json.loads(json.dumps(report))
            forged_lanes["occurrence_lanes"][0]["span_nodes"] = [999]
            with self.assertRaisesRegex(ValueError, "occurrence|lane|report"):
                write_feature_module(
                    module,
                    forged_lanes,
                    root / "lanes",
                    fabric_factory=_RefuseFabric,
                )
            self.assertFalse((root / "lanes").exists())

            forged_findspots = json.loads(json.dumps(report))
            forged_findspots["findspot_audit"]["conflicts"]["16"]["burns_room"] = ["forged"]
            with self.assertRaisesRegex(ValueError, "findspot|report"):
                write_feature_module(
                    module,
                    forged_findspots,
                    root / "findspots",
                    fabric_factory=_RefuseFabric,
                )
            self.assertFalse((root / "findspots").exists())

    def test_refused_tf_save_never_creates_output(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "failed"
            self.assertFalse(
                write_feature_module(
                    module,
                    report,
                    output,
                    fabric_factory=_RefuseFabric,
                )
            )
            self.assertFalse(output.exists())

    def test_unexpected_staged_directory_is_rejected_and_cleaned(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "burns"
            with self.assertRaises(RuntimeError):
                write_feature_module(
                    module,
                    report,
                    output,
                    fabric_factory=_ExtraDirectoryFabric,
                )
            self.assertFalse(output.exists())
            self.assertEqual(tuple(root.iterdir()), ())

    def test_writer_refuses_to_replace_existing_output(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "burns"
            output.mkdir()
            (output / "foreign.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite|exists"):
                write_feature_module(module, report, output)
            self.assertEqual((output / "foreign.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
