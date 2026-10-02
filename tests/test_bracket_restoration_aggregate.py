from __future__ import annotations

import json
import unittest
from types import MappingProxyType

from scripts.audit_burns_alignment import aggregate_bracket_restoration_research
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records
from ugarit_context_parsing.cuc_index import ReviewedCucIndex
from ugarit_context_parsing.source import WorkbookRecord


def _record(row: int, headword: str, line: int) -> WorkbookRecord:
    return WorkbookRecord(
        source_file="01 Synthetic/Worksheet 1.csv",
        source_row=row,
        source_page=row,
        section="Section alpha",
        root="",
        headword=headword,
        ktu="1.14",
        references=f"I.{line}",
        locus="",
        room="",
        point="",
        depth="",
        disputed="",
        comments="private",
    )


def _index() -> ReviewedCucIndex:
    return ReviewedCucIndex(
        compatibility=None,
        tablet_nodes=MappingProxyType({"KTU 1.14": 900}),
        column_nodes=MappingProxyType({("KTU 1.14", "I"): 800}),
        line_nodes=MappingProxyType({
            ("KTU 1.14", "I", 1): 701,
            ("KTU 1.14", "I", 2): 702,
            ("KTU 1.14", "I", 3): 703,
            ("KTU 1.14", "I", 4): 704,
        }),
        bare_line_candidates=MappingProxyType({
            ("KTU 1.14", 1): (701,),
            ("KTU 1.14", 2): (702,),
            ("KTU 1.14", 3): (703,),
            ("KTU 1.14", 4): (704,),
        }),
        line_words=MappingProxyType({
            701: (101,),
            702: (102, 103),
            703: (104,),
            704: (105,),
        }),
        word_g_cons=MappingProxyType({
            101: "abc",
            102: "d",
            103: "e",
            104: "fg",
            105: "h",
        }),
        word_slots=MappingProxyType({
            101: (1, 2, 3),
            102: (4,),
            103: (5,),
            104: (6, 7),
            105: (8,),
        }),
    )


class BracketRestorationAggregateTests(unittest.TestCase):
    def test_aggregate_separates_editorial_support_omitted_group_and_unsupported(self):
        source = normalize_workbook_records((
            _record(1, "[a]bc", 1),
            _record(2, "d ([x]) e", 2),
            _record(3, "[f]g", 3),
            _record(4, "[h]/i", 4),
        ))
        index = _index()
        alignments = align_burns_source(source, index)
        stats = aggregate_bracket_restoration_research(
            source=source,
            alignments=alignments,
            index=index,
            sign_values={1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f", 7: "g", 8: "h"},
            sign_emen={1: "restored"},
            sign_cert={1: "True"},
            sign_alt={},
        )

        self.assertEqual(stats["occurrences"], 4)
        self.assertEqual(
            stats["syntax_classes"],
            {
                "literal_bracket": 2,
                "parenthesis_core_brackets_omitted": 1,
                "unsupported": 1,
            },
        )
        self.assertEqual(
            stats["lexical_outcomes"],
            {"unique": 3, "unsupported": 1},
        )
        self.assertEqual(
            stats["restoration_outcomes"],
            {"exact": 1, "missing": 1},
        )
        self.assertEqual(stats["omitted_bracket_group_unique_matches"], 1)
        self.assertEqual(stats["cert_values_on_exact_restoration"], {"True": 1})
        self.assertEqual(stats["alt_values_on_exact_restoration"], {})

    def test_aggregate_payload_is_source_safe(self):
        source = normalize_workbook_records((_record(1, "[secret]private", 1),))
        index = _index()
        alignments = align_burns_source(source, index)
        payload = json.dumps(
            aggregate_bracket_restoration_research(
                source=source,
                alignments=alignments,
                index=index,
                sign_values={1: "a", 2: "b", 3: "c"},
                sign_emen={},
                sign_cert={},
                sign_alt={},
            ),
            sort_keys=True,
        )
        for restricted in (
            "secret",
            "private",
            "KTU 1.14",
            "I.1",
            source.records[0].record_id,
            source.annotations[0].annotation_id,
        ):
            self.assertNotIn(restricted, payload)


if __name__ == "__main__":
    unittest.main()
