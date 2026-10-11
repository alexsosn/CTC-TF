from __future__ import annotations

import json
import unittest
from dataclasses import replace

from test_headword_candidate_research import _index, _record
from scripts.audit_burns_alignment import aggregate_one_edit_research
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class OneEditResearchTests(unittest.TestCase):
    def test_unique_one_edit_operations_are_directional_and_positioned(self):
        records = (
            _record(1, "abc", 10),     # substitution c -> d
            _record(2, "abc", 20),     # insertion start -> containment precedence
            _record(3, "abc", 30),     # insertion internal
            _record(4, "abc", 40),     # insertion end -> containment precedence
            _record(5, "xabc", 50),    # deletion start
            _record(6, "abxc", 60),    # deletion internal
            _record(7, "abcx", 70),    # deletion end
            _record(8, "abc", 80),     # two distance-1 candidates: ambiguous
            _record(9, "ab", 90),      # unique containment has precedence
            _record(10, "a (b)", 100), # expression syntax: excluded
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                10: ("abd",),
                20: ("xabc",),
                30: ("abxc",),
                40: ("abcx",),
                50: ("abc",),
                60: ("abc",),
                70: ("abc",),
                80: ("abd", "abf"),
                90: ("zabx",),
                100: ("c",),
            }
        )
        alignments = align_burns_source(source, index)

        stats = aggregate_one_edit_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 5)
        self.assertEqual(
            stats["operations"],
            {"deletion": 3, "insertion": 1, "substitution": 1},
        )
        self.assertEqual(stats["substitution_pairs"], {"U+0063>U+0064": 1})
        self.assertEqual(stats["inserted_codepoints"], {"U+0078": 1})
        self.assertEqual(stats["insertion_positions"], {"internal": 1})
        self.assertEqual(stats["deleted_codepoints"], {"U+0078": 3})
        self.assertEqual(
            stats["deletion_positions"],
            {"end": 1, "internal": 1, "start": 1},
        )
        self.assertEqual(
            stats["substitution_pair_positions"],
            {"U+0063>U+0064@end": 1},
        )
        self.assertEqual(
            stats["insertion_codepoint_positions"],
            {"U+0078@internal": 1},
        )
        self.assertEqual(
            stats["deletion_codepoint_positions"],
            {
                "U+0078@end": 1,
                "U+0078@internal": 1,
                "U+0078@start": 1,
            },
        )
        self.assertEqual(
            stats["confusion_distinct_annotations"],
            {
                "deletion:U+0078": 3,
                "insertion:U+0078": 1,
                "substitution:U+0063>U+0064": 1,
            },
        )
        self.assertEqual(stats["ambiguous_distance1_candidates"], 1)
        self.assertEqual(stats["distinct_annotations"], 5)

    def test_repeated_character_edit_positions_are_explicitly_ambiguous(self):
        records = (
            _record(1, "aba", 10),
            _record(2, "abba", 20),
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                10: ("abba",),
                20: ("aba",),
            }
        )
        alignments = align_burns_source(source, index)
        stats = aggregate_one_edit_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 2)
        self.assertEqual(
            stats["operations"],
            {"deletion": 1, "insertion": 1},
        )
        self.assertEqual(
            stats["insertion_positions"],
            {"ambiguous": 1},
        )
        self.assertEqual(
            stats["deletion_positions"],
            {"ambiguous": 1},
        )
        self.assertEqual(
            stats["insertion_codepoint_positions"],
            {"U+0062@ambiguous": 1},
        )
        self.assertEqual(
            stats["deletion_codepoint_positions"],
            {"U+0062@ambiguous": 1},
        )

    def test_repeated_references_do_not_inflate_independent_confusion_evidence(self):
        record = replace(
            _record(1, "abcx", 10),
            references="I.10, 20",
        )
        source = normalize_workbook_records((record,))
        index = _index(
            {
                10: ("abc",),
                20: ("abc",),
            }
        )
        alignments = align_burns_source(source, index)
        stats = aggregate_one_edit_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 2)
        self.assertEqual(stats["distinct_annotations"], 1)
        self.assertEqual(stats["annotation_occurrence_multiplicity"], {"2": 1})
        self.assertEqual(
            stats["confusion_distinct_annotations"],
            {"deletion:U+0078": 1},
        )
        self.assertEqual(
            stats["deletion_codepoint_positions"],
            {"U+0078@end": 2},
        )

    def test_payload_does_not_expose_lexical_strings_ids_locators_or_nodes(self):
        source = normalize_workbook_records((_record(1, "secreta", 10),))
        index = _index({10: ("secretb",)})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_one_edit_research(
                source=source,
                alignments=alignments,
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secreta",
            "secretb",
            "KTU 1.14",
            "I.10",
            source.records[0].record_id,
            source.annotations[0].annotation_id,
            "500",
            "100",
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
