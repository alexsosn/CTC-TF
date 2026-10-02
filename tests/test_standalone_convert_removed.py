from __future__ import annotations

import importlib.util
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from ugarit_context_parsing import cli


ROOT = Path(__file__).resolve().parents[1]


class StandaloneConvertRemovalContractTests(unittest.TestCase):
    def test_public_help_does_not_expose_standalone_convert(self):
        self.assertNotIn("convert", cli._parser().format_help())

    def test_convert_is_not_a_valid_cli_command(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            cli._parser().parse_args([
                "convert", "workbooks",
                "--input-format", "csv",
                "--output", "legacy",
            ])
        self.assertIn("invalid choice", stderr.getvalue())

    def test_standalone_implementation_modules_are_not_importable(self):
        for name in ("graph", "report", "writer", "_semantic_compare"):
            with self.subTest(module=name):
                self.assertIsNone(
                    importlib.util.find_spec(f"ugarit_context_parsing.{name}")
                )

    def test_legacy_agora_materializer_manifest_is_absent(self):
        self.assertFalse((ROOT / "agora.materializer.json").exists())

    def test_public_docs_do_not_advertise_retained_standalone_product(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        for text in (readme, notes):
            self.assertNotIn("burns-workbooks-csv-text-fabric", text)
            self.assertNotIn("burns-workbooks-pdf-text-fabric", text)
        self.assertNotIn("standalone converter remains available", readme.casefold())
        self.assertNotIn("standalone `convert` command is retained", notes)


if __name__ == "__main__":
    unittest.main()
