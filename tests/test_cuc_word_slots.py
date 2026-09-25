from __future__ import annotations

import unittest
from dataclasses import replace
from types import MappingProxyType

from test_cuc_index import SYNTHETIC_COUNTS, snapshot
from ugarit_context_parsing.cuc_index import CucCompatibilityError, _build_index_from_snapshot


WORD_SLOTS = (
    (300, (1,)),
    (301, (2,)),
    (302, (3,)),
    (303, (4,)),
    (304, (5,)),
    (305, (6,)),
)


def build(data):
    return _build_index_from_snapshot(
        data,
        expected_counts=SYNTHETIC_COUNTS,
        expected_section_types=("tablet", "column", "line"),
        expected_section_features=("tablet", "column", "line"),
    )


class CucWordSlotSnapshotTests(unittest.TestCase):
    def test_complete_word_sign_extents_survive_as_read_only_index_identity(self):
        index = build(replace(snapshot(), word_slots=WORD_SLOTS))
        self.assertIsInstance(index.word_slots, MappingProxyType)
        self.assertEqual(index.word_slots[300], (1,))
        self.assertEqual(index.word_slots[305], (6,))
        with self.assertRaises(TypeError):
            index.word_slots[300] = (8,)  # type: ignore[index]

    def test_partial_word_sign_extent_inventory_fails_closed(self):
        data = replace(snapshot(), word_slots=WORD_SLOTS[:-1])
        with self.assertRaisesRegex(CucCompatibilityError, "oslots.*inventory|word.*oslots"):
            build(data)

    def test_duplicate_or_out_of_range_word_slots_fail_closed(self):
        duplicate = replace(snapshot(), word_slots=((*WORD_SLOTS, (300, (7,)))))
        with self.assertRaisesRegex(CucCompatibilityError, "duplicate word oslots"):
            build(duplicate)

        out_of_range = replace(
            snapshot(),
            word_slots=((*WORD_SLOTS[:-1], (305, (9,)))),
        )
        with self.assertRaisesRegex(CucCompatibilityError, "out-of-range oslots"):
            build(out_of_range)


if __name__ == "__main__":
    unittest.main()
