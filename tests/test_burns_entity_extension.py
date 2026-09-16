"""#68 RED: real Text-Fabric search must see distinct overlapping Burns entities.

This is a synthetic CUC proof of an *extended warp*, not a claim that the
existing feature-only v1 module may introduce nodes without a warp change.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_tf_module import _index, _source, _write_synthetic_base
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.entity_extension import build_entity_extension


class BurnsEntityExtensionTests(unittest.TestCase):
    def test_distinct_overlapping_entities_and_multiword_extent_survive_real_tf(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "cuc"
            extension = Path(tmp) / "burns"
            _write_synthetic_base(base)
            original = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            self.assertIsNotNone(original)
            proposed = build_entity_extension(source, alignments, index, original)
            writer = Fabric(locations=[], modules=[], silent="deep")
            self.assertTrue(writer.save(
                nodeFeatures={key: dict(value) for key, value in proposed.node_features.items()},
                edgeFeatures={key: dict(value) for key, value in proposed.edge_features.items()},
                metaData={key: dict(value) for key, value in proposed.metadata.items()},
                location=str(extension), module="", silent="deep",
            ))
            combined = Fabric(locations=[str(base), str(extension)], modules=[""], silent="deep").loadAll(silent="deep")
            self.assertIsNotNone(combined)
            assert combined is not None
            self.assertEqual(combined.F.otype.maxSlot, original.F.otype.maxSlot)
            self.assertEqual(combined.F.otype.maxNode, original.F.otype.maxNode + 5)
            self.assertEqual(tuple(combined.F.otype.s("word")), tuple(original.F.otype.s("word")))
            self.assertEqual(tuple(combined.F.otype.s("entity")), (17, 18, 19, 20, 21))
            self.assertEqual(len(combined.S.search("entity burns_category=divine_name", silent="deep")), 5)
            self.assertEqual(len(combined.S.search("entity burns_headword=bʿl", silent="deep")), 1)
            self.assertEqual(len(combined.S.search("entity burns_headword=bʿl*", silent="deep")), 1)
            self.assertEqual(len(combined.S.search("entity burns_headword=mlk", silent="deep")), 1)
            by_headword = {
                combined.F.burns_headword.v(node): tuple(combined.L.d(node, otype="word"))
                for node in combined.F.otype.s("entity")
            }
            self.assertEqual(by_headword["bʿl"], (8,))
            self.assertEqual(by_headword["bʿl*"], (8,))
            self.assertEqual(by_headword["bʿl mlk"], (10, 11))
            self.assertEqual(by_headword["mlk x"], (11, 12))
            self.assertEqual(by_headword["mlk"], (11,))
            for node in combined.F.otype.s("entity"):
                self.assertEqual(combined.F.burns_category.v(node), "divine_name")
                self.assertIsNone(combined.F.burns_source_file.v(node) if "burns_source_file" in combined.Fall() else None)
            self.assertNotIn("burns_annotations", proposed.node_features)
            self.assertNotIn("burns_source_records", proposed.node_features)

    def test_word_and_tablet_metadata_are_not_claimed_by_entity_labels(self):
        source = _source()
        index = _index()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "cuc"
            _write_synthetic_base(base)
            original = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            extension = build_entity_extension(source, align_burns_source(source, index), index, original)
            self.assertEqual(set(extension.edge_features), {"oslots"})
            self.assertFalse({"locus", "room", "point", "depth", "disputed"} & set(extension.node_features))
            self.assertFalse({"burns_locus", "burns_room", "burns_point", "burns_depth", "burns_disputed"} & set(extension.node_features))
            self.assertEqual(extension.node_features["otype"][16], "tablet")
            self.assertEqual(extension.node_features["otype"][8], "word")
            self.assertEqual(extension.node_features["otype"][17], "entity")


if __name__ == "__main__":
    unittest.main()
