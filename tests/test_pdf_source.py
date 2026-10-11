from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ugarit_context_parsing.pdf_source import load_pdf_directory, parse_workbook_pdf
from ugarit_context_parsing.source import SourceValidationError


class PdfSourceTests(unittest.TestCase):
    @staticmethod
    def _row(headword: str, ktu: str, page: int = 1) -> dict[str, object]:
        return {
            "source_page": page,
            "section": "Section α",
            "root": "",
            "headword": headword,
            "ktu": ktu,
            "references": "synthetic",
            "locus": "GP",
            "room": "",
            "point": "",
            "depth": "",
            "disputed": "n",
            "comments": "synthetic",
        }

    def test_pdf_loader_discovers_stably_and_preserves_parser_results(self):
        calls: list[str] = []

        def fake_parser(path: Path):
            calls.append(path.name)
            return [self._row(path.stem, "1.14" if path.stem == "A" else "1.15")]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("Z/B.pdf", "A/A.pdf"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic pdf bytes")

            source = load_pdf_directory(root, parser=fake_parser)

        self.assertEqual(calls, ["A.pdf", "B.pdf"])
        self.assertEqual(source.files, ("A/A.pdf", "Z/B.pdf"))
        self.assertEqual([record.source_file for record in source.records], ["A/A.pdf", "Z/B.pdf"])
        self.assertEqual([record.source_row for record in source.records], [1, 1])
        self.assertEqual([record.headword for record in source.records], ["A", "B"])
        self.assertRegex(source.tree_sha256, r"^[0-9a-f]{64}$")

    def test_rejects_symlinked_pdf_instead_of_silently_ignoring_it(self):
        def fake_parser(path: Path):
            return [self._row(path.stem, "1.14")]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "A" / "A.pdf"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"synthetic pdf bytes")
            link = root / "B" / "Linked.pdf"
            link.parent.mkdir(parents=True)
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaisesRegex(SourceValidationError, "symlink"):
                load_pdf_directory(root, parser=fake_parser)

    def test_public_pdf_parser_adapter_points_at_the_existing_workbook_parser(self):
        self.assertTrue(callable(parse_workbook_pdf))
        self.assertEqual(parse_workbook_pdf.__name__, "parse_workbook_pdf")


if __name__ == "__main__":
    unittest.main()
