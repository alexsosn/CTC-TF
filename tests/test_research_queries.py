"""Researcher-facing Burns occurrence queries against a saved, combined Text-Fabric API."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_tf_module import _write_synthetic_base
from test_feature_only_module import _fixture
from ugarit_context_parsing.feature_module import write_feature_module
from ugarit_context_parsing.research_queries import iter_burns_occurrences


class ResearchQueryTests(unittest.TestCase):
    def _open_corpus(self, root: Path):
        _, _, _, module, report = _fixture()
        base = root / "base"
        overlay = root / "burns"
        _write_synthetic_base(base)
        self.assertTrue(write_feature_module(module, report, overlay))
        api = Fabric(
            locations=[str(base), str(overlay)], modules=[""], silent="deep"
        ).loadAll(silent="deep")
        self.assertIsNotNone(api)
        return api, base

    def test_all_lanes_preserve_five_distinct_exact_occurrences_and_spans(self):
        with tempfile.TemporaryDirectory() as temp:
            api, _ = self._open_corpus(Path(temp))
            rows = list(iter_burns_occurrences(api))
            self.assertEqual(len(rows), 5)
            self.assertEqual(len({row.occurrence_id for row in rows}), 5)
            self.assertEqual(
                {(row.carrier_node, row.lane) for row in rows},
                {(8, 1), (8, 2), (10, 1), (11, 1), (11, 2)},
            )
            self.assertEqual(
                {row.span_nodes for row in rows},
                {(8,), (10, 11), (11,), (11, 12)},
            )
            self.assertEqual(sum(len(row.span_nodes) > 1 for row in rows), 2)
            self.assertTrue(all(row.category == "divine_name" for row in rows))
            self.assertTrue(all(row.match_rule == "literal" for row in rows))
            self.assertEqual([row.carrier_node for row in rows], [8, 8, 10, 11, 11])

    def test_filters_are_explicit_and_do_not_silently_hide_negative_statuses(self):
        with tempfile.TemporaryDirectory() as temp:
            api, _ = self._open_corpus(Path(temp))
            rows = list(iter_burns_occurrences(api))
            self.assertEqual(len(list(iter_burns_occurrences(api, category="divine_name"))), 5)
            self.assertEqual(len(list(iter_burns_occurrences(api, category="personal_name"))), 0)
            selected = rows[0].semantic_status
            self.assertEqual(
                {x.occurrence_id for x in iter_burns_occurrences(api, semantic_status=selected)},
                {x.occurrence_id for x in rows if x.semantic_status == selected},
            )
            self.assertEqual(
                len(list(iter_burns_occurrences(api, semantic_status="homograph_excluded"))),
                sum(x.semantic_status == "homograph_excluded" for x in rows),
            )

    def test_homograph_exclusions_remain_visible_and_filterable(self):
        from dataclasses import replace

        from test_burns_tf_module import _index, _record
        from ugarit_context_parsing.alignment import align_burns_source
        from ugarit_context_parsing.annotations import normalize_workbook_records
        from ugarit_context_parsing.feature_module import (
            build_feature_module, build_feature_module_report,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            overlay = root / "burns"
            _write_synthetic_base(base)
            source = normalize_workbook_records((
                _record(1, headword="bʿl", references="I.2", section="Section α"),
                replace(
                    _record(2, headword="bʿl", references="I.2", section="Section β"),
                    source_file="02 Synthetic/Worksheet 1.csv",
                ),
            ))
            index = _index()
            alignments = align_burns_source(source, index)
            module = build_feature_module(source, alignments, index)
            report = build_feature_module_report(source, alignments, index, module)
            self.assertTrue(write_feature_module(module, report, overlay))
            api = Fabric(
                locations=[str(base), str(overlay)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            self.assertIsNotNone(api)
            both = tuple(iter_burns_occurrences(api))
            self.assertEqual(len(both), 2)
            self.assertEqual({x.semantic_status for x in both}, {
                "positive_fixed", "homograph_excluded",
            })
            self.assertEqual(
                len(tuple(iter_burns_occurrences(api, semantic_status="positive_fixed"))),
                1,
            )
            self.assertEqual(
                len(tuple(iter_burns_occurrences(api, semantic_status="homograph_excluded"))),
                1,
            )
            self.assertEqual({x.category for x in both}, {"divine_name", "personal_name"})

    def test_missing_multiword_edges_fail_instead_of_underreporting(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            api, _ = self._open_corpus(Path(temp))
            # Adversarial TF facade: all node features remain, but the edge
            # feature that carries multiword members has not been loaded.
            missing_edges = SimpleNamespace(
                Fall=api.Fall,
                Fs=api.Fs,
                Eall=lambda: tuple(
                    feature for feature in api.Eall()
                    if feature != "burns_span_1"
                ),
                Es=api.Es,
                F=api.F,
                N=api.N,
            )
            with self.assertRaisesRegex(ValueError, "missing Burns span edges"):
                list(iter_burns_occurrences(missing_edges))

    def test_filtered_queries_reject_missing_category_instead_of_silent_undercount(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            api, _ = self._open_corpus(Path(temp))
            feature = api.Fs("burns_category_2")
            corrupt_category = SimpleNamespace(
                v=lambda node: None if node == 8 else feature.v(node),
                items=feature.items,
            )
            corrupt_api = SimpleNamespace(
                Fall=api.Fall,
                Fs=lambda name: (
                    corrupt_category if name == "burns_category_2" else api.Fs(name)
                ),
                Eall=api.Eall,
                Es=api.Es,
                F=api.F,
                N=api.N,
            )
            with self.assertRaisesRegex(ValueError, "missing Burns category"):
                list(iter_burns_occurrences(corrupt_api, category="divine_name"))

    def test_required_lane_metadata_missing_fails_closed(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            api, _ = self._open_corpus(Path(temp))
            missing_metadata = SimpleNamespace(
                Fall=lambda: tuple(
                    feature for feature in api.Fall()
                    if feature != "burns_semantic_status_2"
                ),
                Fs=api.Fs,
                Eall=api.Eall,
                Es=api.Es,
                F=api.F,
                N=api.N,
            )
            with self.assertRaisesRegex(ValueError, "incomplete Burns occurrence lane 2"):
                list(iter_burns_occurrences(missing_metadata))

    def test_valid_findspot_only_module_returns_zero_occurrences(self):
        from test_burns_tf_module import _index, _record
        from ugarit_context_parsing.alignment import align_burns_source
        from ugarit_context_parsing.annotations import normalize_workbook_records
        from ugarit_context_parsing.feature_module import (
            build_feature_module, build_feature_module_report,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            overlay = root / "burns"
            _write_synthetic_base(base)
            source = normalize_workbook_records((
                _record(1, headword="not-in-line", references="I.2"),
            ))
            index = _index()
            alignments = align_burns_source(source, index)
            module = build_feature_module(source, alignments, index)
            self.assertEqual(module.max_lane, 0)
            self.assertIn("burns_locus", module.node_features)
            report = build_feature_module_report(source, alignments, index, module)
            self.assertTrue(write_feature_module(module, report, overlay))
            api = Fabric(
                locations=[str(base), str(overlay)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            self.assertIsNotNone(api)
            self.assertEqual(tuple(iter_burns_occurrences(api)), ())

    def test_base_without_burns_module_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp:
            api, base = self._open_corpus(Path(temp))
            base_only = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            self.assertIsNotNone(base_only)
            with self.assertRaisesRegex(ValueError, "Burns.*module|Burns.*features"):
                list(iter_burns_occurrences(base_only))


if __name__ == "__main__":
    unittest.main()
