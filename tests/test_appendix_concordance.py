from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_appendix_cuc_concordance import _read_rows, aggregate_appendix_concordance


def _row(
    *,
    ktu: str,
    rs_number: str,
    locus: str = "",
    room: str = "",
    point: str = "",
    depth: str = "",
    disputed: str = "",
) -> dict[str, str]:
    return {
        "page": "secret-page",
        "ktu": ktu,
        "is_subrow": "",
        "rs_number": rs_number,
        "genre": "secret-genre",
        "locus": locus,
        "room": room,
        "point": point,
        "depth": depth,
        "disputed": disputed,
        "teo_i_p": "secret-teo",
        "sau_p": "secret-sau",
        "comments": "secret-comment",
    }


class AppendixCucConcordanceTests(unittest.TestCase):
    def test_aggregate_concordance_is_source_safe_and_fragment_agnostic(self):
        rows = (
            _row(
                ktu="1.1",
                rs_number="RS secret-a",
                locus="GP-secret",
                room="room-secret-a",
                depth="0.3-secret",
                disputed="n-secret",
            ),
            _row(
                ktu="1.1",
                rs_number="RS secret-b",
                locus="GP-secret",
                room="room-secret-b",
                depth="0.3-secret",
                disputed="n-secret",
            ),
            _row(
                ktu="1.2",
                rs_number="RS secret-c",
                locus="PH-secret",
            ),
            _row(
                ktu="1.2",
                rs_number="RS secret-c",
                locus="",
            ),
            _row(ktu="9.999", rs_number="RS outside-secret"),
            _row(ktu="see secret comments", rs_number="RS invalid-secret"),
        )
        stats = aggregate_appendix_concordance(
            rows=rows,
            cuc_tablets=frozenset({"KTU 1.1", "KTU 1.2"}),
        )

        self.assertEqual(
            stats,
            {
                "source_rows": 6,
                "valid_ktu_rows": 5,
                "invalid_ktu_rows": 1,
                "unique_valid_tablets": 3,
                "tablets_in_cuc": 2,
                "tablets_out_of_cuc": 1,
                "multi_row_tablets": 2,
                "multi_rs_tablets": 1,
                "mapped_multi_rs_tablets": 1,
                "mapped_tablets_with_findspot_conflict": 1,
                "mapped_tablets_with_findspot_incomplete": 1,
                "findspot_conflicts_by_field": {"room": 1},
                "findspot_incomplete_by_field": {"locus": 1},
            },
        )

        payload = json.dumps(stats, sort_keys=True)
        for restricted in (
            "KTU 1.1",
            "RS secret-a",
            "GP-secret",
            "room-secret-a",
            "secret-page",
            "secret-comment",
            "see secret comments",
        ):
            self.assertNotIn(restricted, payload)

    def test_reader_rejects_appendix_schema_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "appendix.csv"
            path.write_text(
                "ktu,rs_number,locus,room,point,depth,disputed\n"
                "1.1,RS synthetic,GP,,,,n\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Appendix CSV header"):
                _read_rows(path)


if __name__ == "__main__":
    unittest.main()
