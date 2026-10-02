from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from tf.fabric import Fabric

from scripts.audit_burns_alignment import aggregate_feature_only_lane_stats
from test_burns_tf_module import _index, _source
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import NormalizedBurnsSource


class FeatureOnlyLaneResearchTests(unittest.TestCase):
    def test_realistic_same_start_collisions_are_counted_losslessly(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)

        stats = aggregate_feature_only_lane_stats(
            source=source,
            alignments=alignments,
            index=index,
        )

        # Synthetic source has:
        # - bʿl and bʿl* both starting at word 8, same exact one-word span;
        # - bʿl mlk starts at word 10;
        # - mlk x and mlk both start at word 11 with distinct spans.
        self.assertEqual(stats["occurrences"], 5)
        self.assertEqual(stats["start_words"], 3)
        self.assertEqual(stats["max_lane"], 2)
        self.assertEqual(
            stats["lanes_per_start"],
            {"1": 1, "2": 2},
        )
        self.assertEqual(
            stats["span_lengths"],
            {"1": 3, "2": 2},
        )
        self.assertEqual(
            stats["identical_span_multiplicity"],
            {"1": 3, "2": 1},
        )
        self.assertEqual(stats["starts_with_multiple_distinct_spans"], 1)
        self.assertEqual(stats["starts_with_multiple_categories"], 0)

    def test_lane_stats_are_order_independent(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)
        forward = aggregate_feature_only_lane_stats(
            source=source,
            alignments=alignments,
            index=index,
        )
        reverse = aggregate_feature_only_lane_stats(
            source=source,
            alignments=tuple(reversed(alignments)),
            index=index,
        )
        self.assertEqual(forward, reverse)

    def test_lane_stats_reject_non_word_anchor_nodes(self):
        source = _source()
        index = _index()
        alignments = list(align_burns_source(source, index))
        first = alignments[0]
        occurrence = replace(first.occurrences[0], anchor_nodes=(13,))
        alignments[0] = replace(first, occurrences=(occurrence,))
        with self.assertRaisesRegex(ValueError, "word"):
            aggregate_feature_only_lane_stats(
                source=source,
                alignments=tuple(alignments),
                index=index,
            )


class TextFabricFeatureOnlyEdgeResearchTests(unittest.TestCase):
    def test_edge_only_module_preserves_base_warp_and_self_edge_is_searchable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            module = root / "module"

            fabric = Fabric(locations=[], modules=[], silent="deep")
            self.assertTrue(
                fabric.save(
                    nodeFeatures={
                        "otype": {
                            1: "sign",
                            2: "sign",
                            3: "word",
                            4: "word",
                        },
                        "g_cons": {3: "a", 4: "b"},
                    },
                    edgeFeatures={
                        "oslots": {
                            3: {1},
                            4: {2},
                        },
                    },
                    metaData={
                        "otype": {"valueType": "str"},
                        "g_cons": {"valueType": "str"},
                        "oslots": {"valueType": "int"},
                        "otext": {"sectionTypes": "", "sectionFeatures": ""},
                    },
                    location=str(base),
                    module="",
                    silent="deep",
                )
            )

            module_fabric = Fabric(locations=[], modules=[], silent="deep")
            self.assertTrue(
                module_fabric.save(
                    nodeFeatures={
                        "burns_occurrence_id_1": {
                            3: "burns-occurrence-sha256:multi",
                            4: "burns-occurrence-sha256:single",
                        },
                        "burns_span_length_1": {3: 2, 4: 1},
                    },
                    edgeFeatures={
                        # Carrier/start is implicit; only subsequent members
                        # are edges so TF Search never depends on self-relations.
                        "burns_span_1": {3: {4}},
                    },
                    metaData={
                        "burns_occurrence_id_1": {"valueType": "str"},
                        "burns_span_length_1": {"valueType": "int"},
                        "burns_span_1": {"valueType": "int"},
                    },
                    location=str(module),
                    module="",
                    silent="deep",
                )
            )

            inventory = {path.name for path in module.glob("*.tf")}
            self.assertEqual(
                inventory,
                {
                    "burns_occurrence_id_1.tf",
                    "burns_span_1.tf",
                    "burns_span_length_1.tf",
                },
            )
            self.assertNotIn("otype.tf", inventory)
            self.assertNotIn("oslots.tf", inventory)

            base_api = Fabric(
                locations=[str(base)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            combined = Fabric(
                locations=[str(base), str(module)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            self.assertIsNotNone(base_api)
            self.assertIsNotNone(combined)
            assert base_api is not None and combined is not None

            self.assertEqual(combined.F.otype.maxSlot, base_api.F.otype.maxSlot)
            self.assertEqual(combined.F.otype.maxNode, base_api.F.otype.maxNode)
            self.assertEqual(tuple(combined.E.oslots.s(3)), tuple(base_api.E.oslots.s(3)))
            self.assertEqual(tuple(combined.E.burns_span_1.f(3)), (3, 4))

            hits = tuple(
                combined.S.search(
                    "s:word burns_occurrence_id_1=burns-occurrence-sha256:synthetic\n"
                    "m:word\n"
                    "s -burns_span_1> m",
                    silent="deep",
                )
            )
            self.assertEqual(set(hits), {(3, 3), (3, 4)})


if __name__ == "__main__":
    unittest.main()
