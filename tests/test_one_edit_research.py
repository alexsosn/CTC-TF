from __future__ import annotations

import json
import unittest

from test_headword_candidate_research import _index, _record
from scripts.audit_burns_alignment import aggregate_one_edit_research
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class OneEditResearchTests(unittest.TestCase):
    def test_unique_one_edit_operations_are_directional_and_positioned(self):
        records = (
            _record(1, "abc", 1),    # substitution c -> d
            _record(2, "abc", 2),    # insertion start
            _record(3, "abc", 3),    # insertion internal
            _record(4, "abc", 4),    # insertion end
            _record(5, "xabc", 5),   # deletion start
            _record(6, "abxc", 6),   # deletion internal
            _record(7, "abcx", 7),   # deletion end
            _record(8, "abc", 8),    # two distance-1 candidates: ambiguous
            _record(9, "ab", 9),     # unique containment has precedence
            _record(10, "a (b)", 10),# expression syntax: excluded
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                1: ("abd",),
                2: ("xabc",),
                3: ("abxc",),
                4: ("abcx",),
                5: ("abc",),
                6: ("abc",),
                7: ("abc",),
                8: ("abd", "abf"),
                9: ("zabx",),
                10: ("c",),
            }
        )
        alignments = align_burns_source(source, index)

        stats = aggregate_one_edit_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 7)
        self.assertEqual(
            stats["operations"],
            {"deletion": 3, "insertion": 3, "substitution": 1},
        )
        self.assertEqual(stats["substitution_pairs"], {"U+0063>U+0064": 1})
        self.assertEqual(stats["inserted_codepoints"], {"U+0078": 3})
        self.assertEqual(
            stats["insertion_positions"],
            {"end": 1, "internal": 1, "start": 1},
        )
        self.assertEqual(stats["deleted_codepoints"], {"U+0078": 3})
        self.assertEqual(
            stats["deletion_positions"],
            {"end": 1, "internal": 1, "start": 1},
        )
        self.assertEqual(stats["ambiguous_distance1_candidates"], 1)
        self.assertEqual(stats["distinct_annotations"], 7)

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
