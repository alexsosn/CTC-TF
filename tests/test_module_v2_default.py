"""#82: primary module command must be the corrected feature-only CUC overlay."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from ugarit_context_parsing import cli


class ModuleV2DefaultTests(unittest.TestCase):

    def test_obsolete_word_projection_prototype_is_not_shipped(self):
        self.assertIsNone(
            importlib.util.find_spec("ugarit_context_parsing.native_features")
        )

    def test_module_is_feature_only_default_and_v1_has_explicit_legacy_command(self):
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
        help_text = parser.format_help()
        self.assertIn("feature-only", help_text)
        self.assertIn("module-v1", help_text)
        self.assertNotIn("entities", help_text)

    def test_entities_alias_is_removed(self):
        parser = cli._parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "entities", "workbooks", "--input-format", "csv",
                "--cuc", "cuc", "--output", "native",
            ])

    def test_primary_module_routes_to_feature_only_writer_not_legacy(self):
        args = [
            "workbooks", "--input-format", "csv",
            "--cuc", "cuc", "--output", "native",
        ]
        with (
            patch.object(cli, "_run_feature_module", return_value=0) as native,
            patch.object(cli, "_run_module", side_effect=AssertionError("v1 used")) as legacy,
        ):
            self.assertEqual(cli.main(["module", *args]), 0)
            native.assert_called_once()
            self.assertEqual(native.call_args.args[0].command, "module")
            legacy.assert_not_called()

    def test_v1_is_only_accessed_via_explicit_compatibility_command(self):
        with (
            patch.object(cli, "_run_feature_module", side_effect=AssertionError("feature module used")) as native,
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
