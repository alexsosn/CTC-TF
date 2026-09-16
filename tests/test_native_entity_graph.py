"""#68 RED: represent overlapping Burns annotation occurrences as real TF nodes."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tf.dataset import modify
from tf.fabric import Fabric

from test_burns_tf_module import _index, _record, _source, _write_synthetic_base
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.entity_graph import build_native_entities


SYNTHETIC_WORD_SLOTS = {node: (node - 6,) for node in range(7, 13)}


class NativeEntityGraphTests(unittest.TestCase):
    def _build(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)
        return build_native_entities(
            source, alignments, index, word_slots=SYNTHETIC_WORD_SLOTS,
            first_node=17,
        )

    def test_each_overlapping_occurrence_has_own_queryable_entity_node(self):
        graph = self._build()
        self.assertEqual(len(graph.node_slots), 5)
        self.assertEqual(tuple(graph.node_slots), (17, 18, 19, 20, 21))
        headwords = graph.node_features["burns_headword"]
        self.assertEqual(sorted(headwords.values()), ["bʿl", "bʿl mlk", "bʿl*", "mlk", "mlk x"])
        b_al_nodes = [n for n, label in headwords.items() if label in ("bʿl", "bʿl*")]
        self.assertEqual(len(b_al_nodes), 2)
        self.assertEqual([graph.node_slots[n] for n in b_al_nodes], [(2,), (2,)])
        self.assertEqual(len(graph.occurrence_nodes), 5)
        self.assertEqual(len(set(graph.occurrence_nodes.values())), 5)
        phrase = next(n for n, label in headwords.items() if label == "bʿl mlk")
        self.assertEqual(graph.node_slots[phrase], (4, 5))
        self.assertEqual(graph.node_features["burns_category"][phrase], "divine_name")
        self.assertEqual(graph.node_features["burns_semantic_status"][phrase], "positive_fixed")
        self.assertNotIn("burns_lemma", graph.node_features)
        self.assertFalse({"burns_annotations", "burns_source_file", "burns_source_row", "burns_locus"} & set(graph.node_features))

    def test_reordered_alignments_stable_and_excluded_and_ambiguous_not_claimed(self):
        source = _source()
        index = _index()
        aligned = align_burns_source(source, index)
        forward = build_native_entities(source, aligned, index, word_slots=SYNTHETIC_WORD_SLOTS, first_node=17)
        backward = build_native_entities(source, tuple(reversed(aligned)), index, word_slots=SYNTHETIC_WORD_SLOTS, first_node=17)
        self.assertEqual(dict(forward.node_slots), dict(backward.node_slots))
        self.assertEqual(dict(forward.node_features), dict(backward.node_features))
        self.assertEqual(dict(forward.occurrence_nodes), dict(backward.occurrence_nodes))

        unsafe = normalize_workbook_records((
            _record(1, headword="bʿl", references="I.2", section="Section β"),
            _record(2, headword="unknown", references="I.3"),  # no exact word span
            _record(3, headword="bʿl", references=""),       # structural tablet, not word
        ))
        excluded = build_native_entities(unsafe, align_burns_source(unsafe, index), index,
                                         word_slots=SYNTHETIC_WORD_SLOTS, first_node=17)
        self.assertFalse(excluded.node_slots)
        self.assertFalse(excluded.occurrence_nodes)
        self.assertEqual(excluded.excluded_occurrences, 3)

    def test_missing_or_duplicate_word_slot_mapping_rejected_without_fabrication(self):
        source = _source()
        index = _index()
        aligned = align_burns_source(source, index)
        missing = {n: v for n, v in SYNTHETIC_WORD_SLOTS.items() if n != 11}
        with self.assertRaises(ValueError):
            build_native_entities(source, aligned, index, word_slots=missing, first_node=17)
        duplicate = {**SYNTHETIC_WORD_SLOTS, 10: (4, 4)}
        with self.assertRaises(ValueError):
            build_native_entities(source, aligned, index, word_slots=duplicate, first_node=17)

    def test_real_tf_derived_corpus_supports_search_and_preserves_occurrence_multiplicity(self):
        graph = self._build()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "cuc"
            target = Path(tmp) / "derived"
            _write_synthetic_base(base)
            result = modify(
                str(base), str(target),
                addTypes={"burnsEntity": {
                    "nodeFrom": 17,
                    "nodeTo": 21,
                    "nodeSlots": {n: set(slots) for n, slots in graph.node_slots.items()},
                    "nodeFeatures": {name: dict(values) for name, values in graph.node_features.items()},
                }},
                featureMeta={name: {"valueType": "str", "description": "Burns entity annotation"}
                             for name in graph.node_features},
                silent="deep",
            )
            self.assertNotEqual(result, False)
            api = Fabric(locations=[str(target)], modules=[""], silent="deep").loadAll(silent="deep")
            self.assertIsNotNone(api)
            assert api is not None
            self.assertEqual(api.F.otype.maxSlot, 6)
            self.assertEqual(len(tuple(api.F.otype.s("burnsEntity"))), 5)
            self.assertEqual(len(api.S.search("burnsEntity burns_headword=bʿl", silent="deep")), 1)
            self.assertEqual(len(api.S.search("burnsEntity burns_headword=bʿl*", silent="deep")), 1)
            self.assertEqual(len(api.S.search("burnsEntity burns_category=divine_name", silent="deep")), 5)
            self.assertEqual(len(api.S.search("burnsEntity burns_headword=bʿl\\ mlk", silent="deep")), 1)
            self.assertEqual(len(api.S.search("burnsEntity burns_semantic_status=positive_fixed", silent="deep")), 5)
            for node in api.F.otype.s("word"):
                self.assertIsNone(api.F.burns_headword.v(node))
            phrase = api.S.search("burnsEntity burns_headword=bʿl\\ mlk", silent="deep")[0][0]
            self.assertEqual(tuple(api.L.d(phrase, otype="sign")), (4, 5))


if __name__ == "__main__":
    unittest.main()
