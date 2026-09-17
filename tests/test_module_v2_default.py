"""#68: primary module command must not silently return the defective v1 JSON output.

This is a public-routing contract, complementary to the real Fabric output and
reviewed-CUC/MCP end-to-end tests. Do not erase the old v1 API without an
explicit compatibility command and a non-overwriting v2 publication policy.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from ugarit_context_parsing import cli


class ModuleV2DefaultTests(unittest.TestCase):
    def test_module_is_native_default_and_v1_has_explicit_legacy_command(self):
        parser = cli._parser()
        native = parser.parse_args([
            "module", "workbooks", "--input-format", "csv",
            "--cuc", "cuc/tf/0.2.8", "--output", "native",
        ])
        legacy = parser.parse_args([
            "module-v1", "workbooks", "--input-format", "csv",
            "--cuc", "cuc/tf/0.2.8", "--output", "legacy",
        ])
        self.assertEqual(native.command, "module")
        self.assertEqual(legacy.command, "module-v1")
        self.assertEqual(native.cuc, Path("cuc/tf/0.2.8"))
        self.assertEqual(legacy.cuc, native.cuc)
        self.assertIn("module-v1", parser.format_help())

    def test_primary_module_and_entities_alias_use_native_writer_not_v1(self):
        args = ["workbooks", "--input-format", "csv", "--cuc", "cuc", "--output", "native"]
        with (
            patch.object(cli, "_run_entities", return_value=0) as native,
            patch.object(cli, "_run_module", side_effect=AssertionError("v1 used")) as legacy,
        ):
            self.assertEqual(cli.main(["module", *args]), 0)
            self.assertEqual(cli.main(["entities", *args]), 0)
            self.assertEqual(native.call_count, 2)
            self.assertEqual([item.args[0].command for item in native.call_args_list], ["module", "entities"])
            legacy.assert_not_called()

    def test_v1_is_only_accessed_via_explicit_compatibility_command(self):
        with (
            patch.object(cli, "_run_entities", side_effect=AssertionError("native used")) as native,
            patch.object(cli, "_run_module", return_value=0) as legacy,
        ):
            self.assertEqual(cli.main([
                "module-v1", "workbooks", "--input-format", "pdf",
                "--cuc", "cuc", "--output", "legacy",
            ]), 0)
            legacy.assert_called_once()
            self.assertEqual(legacy.call_args.args[0].command, "module-v1")
            native.assert_not_called()


if __name__ == "__main__":
    unittest.main()
