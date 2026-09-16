"""#68: combine first-class entities with tablet-only conservative findspots."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_entity_extension import _write_indexed_base
from test_burns_tf_module import _index, _source
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.entity_extension import build_entity_extension


class BurnsEntityFindspotsTests(unittest.TestCase):
    def test_native_tablet_query_and_conflicts_do_not_pollute_words_or_entities(self):
        source, index = _source(), _index()
        with tempfile.TemporaryDirectory() as tmp:
            base, location = Path(tmp) / "base", Path(tmp) / "module"
            _write_indexed_base(base)
            original = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            extension = build_entity_extension(source, align_burns_source(source, index), index, original)
            self.assertEqual(extension.node_features["burns_locus"], {16: "GP"})
            self.assertFalse(extension.node_features.get("burns_room"))
            self.assertEqual(extension.findspot_audit.conflicts[16]["burns_room"], (
                "R1", "R2", "R3", "R4", "R5",
            ))
            self.assertIn("burns_point", extension.findspot_audit.incomplete[16])
            self.assertTrue(Fabric(locations=[], modules=[], silent="deep").save(
                nodeFeatures={name: dict(nodes) for name, nodes in extension.node_features.items()},
                edgeFeatures={name: dict(nodes) for name, nodes in extension.edge_features.items()},
                metaData={name: dict(meta) for name, meta in extension.metadata.items()},
                location=str(location), module="", silent="deep",
            ))
            combined = Fabric(locations=[str(base), str(location)], modules=[""], silent="deep").loadAll(silent="deep")
            self.assertEqual(tuple(combined.S.search("tablet burns_locus=GP", silent="deep")), ((16,),))
            self.assertIsNone(combined.F.burns_locus.v(8))
            for entity in combined.F.otype.s("entity"):
                self.assertIsNone(combined.F.burns_locus.v(entity))
            self.assertNotIn("burns_annotations", combined.Fall())
            self.assertNotIn("burns_source_row", combined.Fall())


if __name__ == "__main__":
    unittest.main()
