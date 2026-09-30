from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from ugarit_context_parsing import cli


ROOT = Path(__file__).resolve().parents[1]


class StandaloneConvertRemovalContractTests(unittest.TestCase):
    def test_public_help_does_not_expose_standalone_convert(self):
        help_text = cli._parser().format_help()
        self.assertNotIn("convert", help_text)

    def test_convert_is_not_a_valid_cli_command(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            cli._parser().parse_args([
                "convert",
                "workbooks",
                "--input-format",
                "csv",
                "--output",
                "legacy",
            ])
        self.assertIn("invalid choice", stderr.getvalue())

    def test_legacy_agora_materializer_manifest_is_removed(self):
        self.assertFalse(
            (ROOT / "agora.materializer.json").exists(),
            "standalone convert materializers must not remain advertised upstream",
        )


if __name__ == "__main__":
    unittest.main()
