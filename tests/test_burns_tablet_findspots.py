"""#68: source archaeological observations cannot be repeated on word nodes."""
from __future__ import annotations

import unittest
from dataclasses import replace

from test_burns_tf_module import _index, _record
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.tablet_findspots import derive_tablet_findspots


class BurnsTabletFindspotsTests(unittest.TestCase):
    def test_consistent_repeated_observations_are_one_tablet_value(self):
        source = normalize_workbook_records((
            replace(_record(1, headword="bʿl", references="I.2"), room="R", point=""),
            replace(_record(2, headword="mlk", references="I.3"), room="R", point=""),
        ))
        derived = derive_tablet_findspots(source, _index())
        self.assertEqual(derived.node_features["burns_locus"], {16: "GP"})
        self.assertEqual(derived.node_features["burns_room"], {16: "R"})
        self.assertEqual(derived.node_features["burns_point"], {})
        self.assertEqual(derived.conflicts, {})
        self.assertEqual(derived.incomplete, {})
        for feature in derived.node_features.values():
            self.assertEqual(set(feature) - {16}, set())

    def test_conflicting_tablet_observations_are_not_arbitrarily_selected(self):
        source = normalize_workbook_records((
            _record(1, headword="bʿl", references="I.2"),
            _record(2, headword="mlk", references="I.3"),
        ))
        derived = derive_tablet_findspots(source, _index())
        self.assertEqual(derived.node_features["burns_locus"], {16: "GP"})
        self.assertEqual(derived.node_features["burns_room"], {})
        self.assertEqual(derived.conflicts[16]["burns_room"], ("R1", "R2"))
        self.assertEqual(derived.incomplete, {})

    def test_missing_observation_never_promotes_single_fragment_to_whole_tablet(self):
        source = normalize_workbook_records((
            _record(1, headword="bʿl", references="I.2", point="P"),
            _record(2, headword="mlk", references="I.3", point=""),
        ))
        derived = derive_tablet_findspots(source, _index())
        self.assertEqual(derived.node_features["burns_point"], {})
        self.assertIn("burns_point", derived.incomplete[16])
        self.assertNotIn(16, derived.node_features["burns_room"])

    def test_unmapped_or_nontextual_ktu_cannot_contribute_tablet_values(self):
        source = normalize_workbook_records((
            replace(_record(1, headword="bʿl", references="I.2"), ktu="9.99"),
            replace(_record(2, headword="mlk", references="I.3"), ktu="Not attested"),
        ))
        derived = derive_tablet_findspots(source, _index())
        self.assertTrue(all(not nodes for nodes in derived.node_features.values()))
        self.assertEqual(set(derived.unmapped_record_ids), {row.record_id for row in source.records})

    def test_input_record_order_does_not_change_projection_or_conflict_manifest(self):
        source = normalize_workbook_records((
            _record(1, headword="bʿl", references="I.2"),
            _record(2, headword="mlk", references="I.3"),
        ))
        first = derive_tablet_findspots(source, _index())
        second = derive_tablet_findspots(replace(source, records=tuple(reversed(source.records))), _index())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
