"""#68: causal RED contracts for safe, native TF node-feature projections.

These tests deliberately do not assert that feature-only modules add `entity`
nodes. That architectural migration and publishing integration are separate
gates documented in research/issue-68/PLAN.md.
"""
from __future__ import annotations

import unittest
from dataclasses import replace
from types import MappingProxyType

from test_burns_tf_module import _index, _record, _source
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.native_features import CATEGORY_FEATURES, derive_native_features


class NativeBurnsFeaturesTests(unittest.TestCase):
    def test_all_nine_categories_are_explicit_and_native_scalars(self):
        self.assertEqual(
            CATEGORY_FEATURES,
            {
                1: "burns_in_divine_name",
                2: "burns_in_personal_name",
                3: "burns_in_geographical_name",
                4: "burns_in_cultic_jargon",
                5: "burns_in_cultic_commodity",
                6: "burns_in_cultic_location",
                7: "burns_in_cultic_time_event",
                8: "burns_in_cultic_personnel",
                9: "burns_in_cultic_action",
            },
        )
        records = tuple(
            replace(
                _record(ordinal, headword="bʿl", references="I.2", section=("Section α" if ordinal < 5 else "Section α1")),
                source_file=f"{ordinal:02d} Synthetic/Worksheet 1.csv",
            )
            for ordinal in range(1, 10)
        )
        source = normalize_workbook_records(records)
        index = _index()
        features = derive_native_features(source, align_burns_source(source, index), index)
        for ordinal, name in CATEGORY_FEATURES.items():
            with self.subTest(category=ordinal):
                self.assertEqual(features.node_features[name], {8: 1})
                self.assertEqual(type(features.node_features[name][8]), int)
        self.assertNotIn(13, features.node_features["burns_in_divine_name"])

    def test_different_headwords_on_same_word_are_not_silently_overwritten(self):
        source = _source()
        index = _index()
        features = derive_native_features(source, align_burns_source(source, index), index)
        self.assertNotIn(8, features.node_features["burns_headword"])
        self.assertEqual(
            features.headword_collisions[8],
            ("bʿl", "bʿl*"),
        )
        # The original overlap is still useful as a native category predicate.
        self.assertEqual(features.node_features["burns_in_divine_name"][8], 1)

    def test_phrase_membership_does_not_assign_phrase_lemma_to_each_token(self):
        source = _source()
        index = _index()
        features = derive_native_features(source, align_burns_source(source, index), index)
        self.assertNotIn(10, features.node_features["burns_headword"])
        self.assertEqual(features.node_features["burns_headword"][11], "mlk")
        self.assertNotIn(12, features.node_features["burns_headword"])
        for node in (10, 11, 12):
            self.assertEqual(features.node_features["burns_in_divine_name"][node], 1)
        self.assertNotIn("burns_lemma", features.node_features)

    def test_root_is_a_single_word_source_label_not_a_guess(self):
        source = normalize_workbook_records(
            (
                replace(
                    _record(1, headword="mlk", references="I.3", root="MLK"),
                    source_file="09 Synthetic/Worksheet 1.csv",
                    section="Section α1",
                ),
                replace(
                    _record(2, headword="mlk*", references="I.3", root="MLK2"),
                    source_file="09 Synthetic/Worksheet 1.csv",
                    section="Section α1",
                ),
            )
        )
        index = _index()
        features = derive_native_features(source, align_burns_source(source, index), index)
        self.assertNotIn(11, features.node_features["burns_root"])
        self.assertEqual(features.root_collisions[11], ("MLK", "MLK2"))
        self.assertEqual(features.node_features["burns_in_cultic_action"], {11: 1})

    def test_ambiguous_and_unselected_anchors_make_no_word_level_claims(self):
        source = normalize_workbook_records(
            (
                _record(1, headword="bʿl", references="I.2"),
                _record(2, headword="unknown", references="I.2"),
                _record(3, headword="mlk", references=""),
            )
        )
        original = _index()
        # Genuine repeated homograph: two distinct CUC word nodes on line I.2
        # now read bʿl, so alignment must stay at line level rather than guess.
        index = replace(
            original,
            word_g_cons=MappingProxyType({**original.word_g_cons, 7: "bʿl"}),
        )
        features = derive_native_features(source, align_burns_source(source, index), index)
        for name in CATEGORY_FEATURES.values():
            self.assertFalse(features.node_features[name])
        self.assertFalse(features.node_features["burns_headword"])
        self.assertFalse(features.node_features["burns_root"])

    def test_output_deterministic_for_alignment_order_and_does_not_copy_findspots(self):
        source = _source()
        index = _index()
        alignments = align_burns_source(source, index)
        first = derive_native_features(source, alignments, index)
        second = derive_native_features(source, tuple(reversed(alignments)), index)
        self.assertEqual(dict(first.node_features), dict(second.node_features))
        self.assertEqual(dict(first.headword_collisions), dict(second.headword_collisions))
        self.assertEqual(dict(first.root_collisions), dict(second.root_collisions))
        self.assertFalse({"locus", "room", "point", "depth", "disputed"} & set(first.node_features))
        self.assertFalse({"burns_annotations", "burns_annotation_ids", "source_row"} & set(first.node_features))


if __name__ == "__main__":
    unittest.main()
