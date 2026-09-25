"""#68 native TF consumer queries for roots, workbooks and negative status.

Exact-word duplicates in different Burns Workbooks remain distinct entity
nodes. A category query alone includes excluded homographs by design; the
independent semantic-status feature allows explicit positive-only queries.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tf.fabric import Fabric

from test_burns_entity_extension import _write_indexed_base
from test_burns_tf_module import _index, _record
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.entity_extension import build_entity_extension


class BurnsNativeQueryMatrixTests(unittest.TestCase):
    def test_root_and_two_categories_and_negative_status_are_native_tf_predicates(self):
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
        with tempfile.TemporaryDirectory() as tmp:
            base, location = Path(tmp) / "base", Path(tmp) / "burns"
            _write_indexed_base(base)
            api = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            extension = build_entity_extension(source, align_burns_source(source, index), index, api)
            self.assertTrue(Fabric(locations=[], modules=[], silent="deep").save(
                nodeFeatures={name: dict(nodes) for name, nodes in extension.node_features.items()},
                edgeFeatures={name: dict(nodes) for name, nodes in extension.edge_features.items()},
                metaData={name: dict(meta) for name, meta in extension.metadata.items()},
                location=str(location), module="", silent="deep",
            ))
            tf = Fabric(locations=[str(base), str(location)], modules=[""], silent="deep").loadAll(silent="deep")
            roots = tuple(tf.S.search("entity burns_root=MLK", silent="deep"))
            actions = tuple(tf.S.search("entity burns_category=cultic_action", silent="deep"))
            names = tuple(tf.S.search("entity burns_category=personal_name", silent="deep"))
            excluded = tuple(tf.S.search("entity burns_semantic_status=homograph_excluded", silent="deep"))
            positive_names = tuple(tf.S.search(
                "entity burns_category=personal_name burns_semantic_status=positive_fixed",
                silent="deep",
            ))
            self.assertEqual(len(roots), len(actions))
            self.assertEqual(len(actions), len(names))
            self.assertEqual(len(names), len(excluded))
            self.assertEqual(len(roots), 1)
            self.assertEqual(roots, actions)
            self.assertEqual(names, excluded)
            self.assertNotEqual(actions, names)
            self.assertEqual(positive_names, ())
            self.assertEqual(tuple(tf.L.d(roots[0][0], otype="word")), (11,))
            self.assertEqual(tuple(tf.L.d(names[0][0], otype="word")), (11,))
            self.assertEqual(tf.F.burns_root.v(names[0][0]), None)
            self.assertNotIn("burns_lemma", tf.Fall())


if __name__ == "__main__":
    unittest.main()
