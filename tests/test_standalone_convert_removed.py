from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path
import unittest

from ugarit_context_parsing import cli


ROOT = Path(__file__).resolve().parents[1]
_REMOVED_MODULES = (
    "ugarit_context_parsing.graph",
    "ugarit_context_parsing.report",
    "ugarit_context_parsing.writer",
    "ugarit_context_parsing._semantic_compare",
)


class StandaloneConvertRemovalContractTests(unittest.TestCase):
    def test_cli_help_no_longer_exposes_convert(self):
        help_text = cli._parser().format_help()
        self.assertNotIn("convert", help_text)
        self.assertIn("module", help_text)
        self.assertIn("module-v1", help_text)

    def test_convert_is_rejected_as_unknown_command(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            cli._parser().parse_args(["convert"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_legacy_agora_materializer_manifest_is_absent(self):
        self.assertFalse((ROOT / "agora.materializer.json").exists())

    def test_standalone_runtime_modules_are_not_installed(self):
        for module in _REMOVED_MODULES:
            with self.subTest(module=module):
                self.assertIsNone(importlib.util.find_spec(module))

    def test_readme_does_not_advertise_standalone_corpus_or_manifest(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").casefold()
        self.assertNotIn("standalone converter remains available", readme)
        self.assertNotIn("legacy single-input", readme)
        self.assertNotIn("agora.materializer.json", readme)
        self.assertNotIn("burns-workbooks-csv-text-fabric", readme)
        self.assertNotIn("burns-workbooks-pdf-text-fabric", readme)


if __name__ == "__main__":
    unittest.main()
