"""Regression tests for the CUC snapshot boundary (issue #156)."""
from types import SimpleNamespace
import unittest

from ugarit_context_parsing.cuc_index import (
    CucCompatibilityError,
    _build_index_from_snapshot,
    _snapshot_from_tf,
)


COUNTS = {"sign": 3, "alias": 1, "boundary": 1, "column": 1,
          "line": 1, "tablet": 1, "word": 1}
SECTIONS = ("tablet", "column", "line")


def fake_api(label, *, extra_type=None):
    types = {
        "sign": (1, 2, 3), "alias": (4,), "boundary": (5,),
        "column": (6,), "line": (7,), "tablet": (8,), "word": (9,),
    }
    if extra_type:
        types[extra_type] = (10,)
    return SimpleNamespace(
        F=SimpleNamespace(
            otype=SimpleNamespace(
                s=lambda name: types.get(name, ()),
                items=lambda: ((n, name) for name, nodes in types.items() for n in nodes),
            ),
            tablet=SimpleNamespace(v=lambda n: "KTU 1.1"),
            g_cons=SimpleNamespace(v=lambda n: "mlk"),
        ),
        E=SimpleNamespace(oslots=SimpleNamespace(s=lambda n: (1, 2, 3))),
        T=SimpleNamespace(sectionFromNode=lambda n:
                          ("KTU 1.1", "I") if n == 6 else ("KTU 1.1", "I", label)),
        L=SimpleNamespace(d=lambda n, otype: (9,)),
    )


def extract(label, *, feature="line_label", extra_type=None):
    return _snapshot_from_tf(
        fake_api(label, extra_type=extra_type),
        section_types=SECTIONS,
        section_features=("tablet", "column", feature),
    )


class CucSnapshotSchemaTests(unittest.TestCase):
    def test_snapshot_counts_actual_types_including_alias_and_boundary(self):
        snapshot = extract("1")
        self.assertEqual(dict(snapshot.counts), COUNTS)
        index = _build_index_from_snapshot(
            snapshot,
            expected_counts=COUNTS,
            expected_section_types=SECTIONS,
            expected_section_features=("tablet", "column", "line_label"),
        )
        self.assertEqual(index.line_nodes[("KTU 1.1", "I", 1)], 7)
        self.assertEqual(index.word_slots[9], (1, 2, 3))

    def test_unexpected_type_cannot_disappear_from_inventory(self):
        snapshot = extract("1", extra_type="unexpected")
        self.assertEqual(dict(snapshot.counts), {**COUNTS, "unexpected": 1})
        with self.assertRaisesRegex(CucCompatibilityError, "count mismatch"):
            _build_index_from_snapshot(
                snapshot,
                expected_counts=COUNTS,
                expected_section_types=SECTIONS,
                expected_section_features=("tablet", "column", "line_label"),
            )

    def test_legacy_integer_and_new_canonical_string_are_equivalent(self):
        old = extract(1, feature="line")
        new = extract("1")
        self.assertEqual(old.lines, new.lines)

    def test_noncanonical_line_labels_are_not_silently_coerced(self):
        # The existing Burns reference model has integer line numbers only.
        # Until a source-backed addressing policy exists, reject rather than
        # alias a distinct printed address to an ordinary numbered line.
        for label in ("1a", "1'", "01", " 1", "1 ", "+1", "١", "1_0", 1.5, True):
            with self.subTest(label=label):
                with self.assertRaises(CucCompatibilityError):
                    extract(label)


if __name__ == "__main__":
    unittest.main()
