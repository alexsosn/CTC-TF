from __future__ import annotations

import json
import unittest
from dataclasses import replace

from scripts.audit_burns_alignment import aggregate_containment_research
from test_headword_candidate_research import _index, _record
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class ContainmentResearchTests(unittest.TestCase):
    def test_unique_containment_structure_is_directional_and_source_safe(self):
        repeated = replace(
            _record(8, "ab", 70),
            references="I.70, 80",
        )
        records = (
            _record(1, "ab", 10),       # right extra m
            _record(2, "ab", 20),       # left extra m
            _record(3, "ab", 30),       # both: m + n
            _record(4, "ab", 40),       # right extra mn
            _record(5, "ab", 50),       # two containing candidates -> ambiguous
            _record(6, "ab", 60),       # current containment but neighbor exact wins
            _record(7, "a (b)", 65),    # expression syntax excluded
            repeated,
        )
        source = normalize_workbook_records(records)
        index = _index(
            {
                10: ("abm",),
                20: ("mab",),
                30: ("mabn",),
                40: ("abmn",),
                50: ("abm", "abn"),
                60: ("abm",),
                61: ("ab",),
                65: ("axb",),
                70: ("abm",),
                80: ("abm",),
            }
        )
        alignments = align_burns_source(source, index)

        stats = aggregate_containment_research(
            source=source,
            alignments=alignments,
            index=index,
        )

        self.assertEqual(stats["occurrences"], 6)
        self.assertEqual(stats["ambiguous_containing_candidates"], 1)
        self.assertEqual(
            stats["side_classes"],
            {"both": 1, "left_only": 1, "right_only": 4},
        )
        self.assertEqual(stats["left_extra_lengths"], {"1": 2})
        self.assertEqual(stats["right_extra_lengths"], {"1": 4, "2": 1})
        self.assertEqual(stats["left_extra_codepoints"], {"U+006D": 2})
        self.assertEqual(
            stats["right_extra_codepoints"],
            {"U+006D": 4, "U+006E": 2},
        )
        self.assertEqual(stats["distinct_annotations"], 5)
        self.assertEqual(
            stats["annotation_occurrence_multiplicity"],
            {"1": 4, "2": 1},
        )
        self.assertEqual(
            stats["extra_codepoint_distinct_annotations"],
            {
                "left:U+006D": 2,
                "right:U+006D": 3,
                "right:U+006E": 2,
            },
        )

    def test_repeated_token_inside_one_cuc_word_is_ambiguous_not_a_left_or_right_affix(self):
        source = normalize_workbook_records(
            (_record(1, "aba", 10), _record(2, "aa", 20))
        )
        index = _index({
            10: ("ababa",),  # two overlapping placements, left or right extra
            20: ("aaa",),    # overlapping repeated-token placements
        })
        alignments = align_burns_source(source, index)
        stats = aggregate_containment_research(
            source=source, alignments=alignments, index=index
        )
        self.assertEqual(stats["occurrences"], 2)
        self.assertEqual(stats["ambiguous_token_embeddings"], 2)
        self.assertEqual(stats["side_classes"], {"ambiguous_embedding": 2})
        self.assertEqual(stats["left_extra_codepoints"], {})
        self.assertEqual(stats["right_extra_codepoints"], {})

    def test_payload_does_not_expose_lexical_strings_ids_locators_or_nodes(self):
        source = normalize_workbook_records((_record(1, "secret", 10),))
        index = _index({10: ("secretx",)})
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_containment_research(
                source=source,
                alignments=alignments,
                index=index,
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret",
            "secretx",
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
