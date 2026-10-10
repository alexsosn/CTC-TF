from __future__ import annotations

import json
import unittest
from dataclasses import replace
from types import MappingProxyType

from scripts.audit_burns_alignment import aggregate_empty_g_cons_boundary_research
from test_headword_candidate_research import _index, _record
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class EmptyGConsBoundaryResearchTests(unittest.TestCase):
    def _fixture(self):
        record = replace(_record(1, "ab cd", 10), references="I.10, 20")
        source = normalize_workbook_records((record,))
        index = _index({10: ("ab", "", "cd"), 20: ("ab", "", "cd"), 30: ("x", "")})
        alignments = align_burns_source(source, index)
        return source, index, alignments

    def test_aggregate_counts_window_and_sign_feature_presence_without_word_data(self):
        source, index, alignments = self._fixture()
        # Fixture's sign slots are 1,2,3 for line 10; 4,5,6 for line 20;
        # 7,8 for unreferenced line 30. All are synthetic.
        stats = aggregate_empty_g_cons_boundary_research(
            source=source, alignments=alignments, index=index,
            sign_values={2: "editorial", 5: "editorial"},
            sign_emen={2: "editorial"},
            sign_cert={5: "editorial"},
            sign_alt={2: "editorial", 8: "editorial"},
        )
        self.assertEqual(stats["occurrences_with_empty_g_cons"], 2)
        self.assertEqual(stats["target_windows_with_empty_g_cons"], 2)
        self.assertEqual(stats["distinct_burns_annotations"], 1)
        self.assertEqual(stats["all_cuc_empty_words"], 3)
        self.assertEqual(stats["boundary_unique_cuc_empty_words"], 2)
        self.assertEqual(stats["empty_word_window_positions"], {"middle": 2})
        self.assertEqual(stats["all_empty_word_sign_slot_counts"], {"1": 3})
        self.assertEqual(
            stats["all_empty_word_feature_presence"],
            {"alt": 2, "cert": 1, "emen": 1, "sign": 2},
        )
        self.assertEqual(
            stats["boundary_empty_word_feature_presence"],
            {"alt": 1, "cert": 1, "emen": 1, "sign": 2},
        )

    def test_absent_word_slot_extent_fails_closed(self):
        source, index, alignments = self._fixture()
        broken = replace(index, word_slots=MappingProxyType({}))
        with self.assertRaisesRegex(ValueError, "missing sign extent"):
            aggregate_empty_g_cons_boundary_research(
                source=source, alignments=alignments, index=broken,
                sign_values={}, sign_emen={}, sign_cert={}, sign_alt={},
            )

    def test_no_lexical_strings_ids_or_locators_in_payload(self):
        source = normalize_workbook_records((_record(1, "secret private", 10),))
        index = _index({10: ("secret", "", "private")})
        alignments = align_burns_source(source, index)
        payload = json.dumps(aggregate_empty_g_cons_boundary_research(
            source=source, alignments=alignments, index=index,
            sign_values={2: "private-sign-value"},
            sign_emen={2: "private-emendation"},
            sign_cert={2: "private-certainty"},
            sign_alt={2: "private-alternative"},
        ), sort_keys=True)
        for forbidden in (
            "secret", "private", "private-sign-value", "private-emendation",
            "private-certainty", "private-alternative", "KTU 1.14", "I.10", "500",
            source.records[0].record_id, source.annotations[0].annotation_id,
        ):
            self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()
