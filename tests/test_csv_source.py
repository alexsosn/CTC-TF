from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ugarit_context_parsing.identifiers import normalize_cuc_tablet
from ugarit_context_parsing.source import WORKBOOK_FIELDS, SourceValidationError, load_csv_directory


class CucIdentifierTests(unittest.TestCase):
    def test_normalizes_real_ktu_identifiers_without_touching_source_value(self):
        self.assertEqual(normalize_cuc_tablet("1.14"), "KTU 1.14")
        self.assertEqual(normalize_cuc_tablet(" KTU 1.14 "), "KTU 1.14")
        self.assertEqual(normalize_cuc_tablet("2.105"), "KTU 2.105")
        self.assertEqual(normalize_cuc_tablet("Not attested"), "")
        self.assertEqual(normalize_cuc_tablet("Not attested (cf. above)"), "")
        self.assertEqual(normalize_cuc_tablet("see comments"), "")


class CsvSourceTests(unittest.TestCase):
    def _write_csv(self, path: Path, rows: list[dict[str, object]], *, fields=None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(fields or WORKBOOK_FIELDS)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _row(**overrides) -> dict[str, object]:
        row: dict[str, object] = {
            "source_page": 1,
            "section": "Section α",
            "root": "",
            "headword": "bʿl",
            "ktu": "1.14",
            "references": "I 1-2",
            "locus": "GP",
            "room": "1",
            "point": "3",
            "depth": "0.5",
            "disputed": "n",
            "comments": "synthetic test row",
        }
        row.update(overrides)
        return row

    def test_loads_recursive_csvs_in_stable_path_order_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_csv(root / "B" / "Worksheet 2.csv", [self._row(headword="ym", ktu="1.2")])
            self._write_csv(
                root / "A" / "Worksheet 1.csv",
                [
                    self._row(),
                    self._row(source_page=2, headword="špš", ktu="Not attested", locus=""),
                ],
            )

            source = load_csv_directory(root)

        self.assertEqual([record.source_file for record in source.records], [
            "A/Worksheet 1.csv",
            "A/Worksheet 1.csv",
            "B/Worksheet 2.csv",
        ])
        self.assertEqual([record.source_row for record in source.records], [1, 2, 1])
        self.assertEqual(source.records[0].headword, "bʿl")
        self.assertEqual(source.records[0].ktu, "1.14")
        self.assertEqual(source.records[0].comments, "synthetic test row")
        self.assertEqual(source.records[1].source_page, 2)

    def test_ignores_root_level_appendix_csv_when_workbooks_are_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_csv(root / "appendix.csv", [{"ktu": "1.1"}], fields=["ktu"])
            self._write_csv(root / "Divine Names" / "Names.csv", [self._row()])
            source = load_csv_directory(root)

        self.assertEqual(source.files, ("Divine Names/Names.csv",))
        self.assertEqual(len(source.records), 1)

    def test_rejects_non_workbook_csv_header_inside_workbook_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_csv(root / "Workbook" / "invalid.csv", [{"ktu": "1.1"}], fields=["ktu"])
            with self.assertRaisesRegex(SourceValidationError, "Workbook CSV header"):
                load_csv_directory(root)

    def test_rejects_extra_csv_cells_instead_of_dropping_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "Workbook" / "Worksheet.csv"
            self._write_csv(path, [self._row()])
            lines = path.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1] + ",unexpected-extra-cell"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SourceValidationError, "column count"):
                load_csv_directory(root)

    def test_rejects_missing_csv_cells_instead_of_coercing_them_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "Workbook" / "Worksheet.csv"
            self._write_csv(path, [self._row()])
            lines = path.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1].rsplit(",", 1)[0]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SourceValidationError, "column count"):
                load_csv_directory(root)

    def test_rejects_symlinked_csv_instead_of_silently_ignoring_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "A" / "Worksheet.csv"
            self._write_csv(target, [self._row()])
            link = root / "B" / "Linked.csv"
            link.parent.mkdir(parents=True)
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaisesRegex(SourceValidationError, "symlink"):
                load_csv_directory(root)

    def test_rejects_invalid_source_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_csv(root / "Workbook" / "Worksheet.csv", [self._row(source_page="zero")])
            with self.assertRaisesRegex(SourceValidationError, "source_page"):
                load_csv_directory(root)


if __name__ == "__main__":
    unittest.main()
