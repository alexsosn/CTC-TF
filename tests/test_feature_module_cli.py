"""Public CLI safety contracts for the corrected feature-only Burns module."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ugarit_context_parsing import cli


class FeatureModuleCliTests(unittest.TestCase):
    def test_module_routes_validated_source_and_reviewed_index_to_feature_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source"
            source_path.mkdir()
            cuc = root / "cuc"
            cuc.mkdir()
            output = root / "module"
            source = SimpleNamespace(root=source_path, records=("raw",), files=("01.csv",))
            normalized = SimpleNamespace(records=(1,), annotations=(1,))
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "normalize_workbook_records", return_value=normalized),
                patch.object(cli, "build_reviewed_cuc_index", return_value="reviewed-index") as index,
                patch.object(cli, "align_burns_source", return_value=("alignment",)),
                patch.object(cli, "build_feature_module", return_value="module-data") as build,
                patch.object(cli, "build_feature_module_report", return_value="report") as report,
                patch.object(cli, "write_feature_module", return_value=True) as writer,
                redirect_stdout(io.StringIO()) as output_text,
            ):
                self.assertEqual(cli.main([
                    "module", str(source_path), "--input-format", "csv",
                    "--cuc", str(cuc), "--output", str(output),
                ]), 0)
                index.assert_called_once_with(cuc)
                build.assert_called_once_with(normalized, ("alignment",), "reviewed-index")
                report.assert_called_once_with(normalized, ("alignment",), "reviewed-index", "module-data")
                writer.assert_called_once_with("module-data", "report", output)
                self.assertIn("feature-only Burns module", output_text.getvalue())

    def test_module_rejects_source_or_cuc_output_overlap_before_indexing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source"
            source_path.mkdir()
            cuc = root / "cuc"
            cuc.mkdir()
            source = SimpleNamespace(root=source_path, records=(), files=())
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "build_reviewed_cuc_index") as index,
            ):
                for output in (source_path, source_path / "child", cuc, cuc / "child"):
                    with self.subTest(output=output), self.assertRaises(SystemExit):
                        cli.main([
                            "module", str(source_path), "--input-format", "csv",
                            "--cuc", str(cuc), "--output", str(output),
                        ])
                index.assert_not_called()

    def test_relative_reviewed_cuc_path_is_validated_as_supplied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source"
            source_path.mkdir()
            cuc = root / "cuc"
            cuc.mkdir()
            output = root / "module"
            relative_cuc = os.path.relpath(cuc, Path.cwd())
            source = SimpleNamespace(root=source_path, records=("raw",), files=("01.csv",))
            normalized = SimpleNamespace(records=(1,), annotations=(1,))
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "normalize_workbook_records", return_value=normalized),
                patch.object(cli, "build_reviewed_cuc_index", return_value="reviewed-index") as index,
                patch.object(cli, "align_burns_source", return_value=("alignment",)),
                patch.object(cli, "build_feature_module", return_value="module-data"),
                patch.object(cli, "build_feature_module_report", return_value="report"),
                patch.object(cli, "write_feature_module", return_value=True),
                redirect_stdout(io.StringIO()) as output_text,
            ):
                self.assertEqual(cli.main([
                    "module", str(source_path), "--input-format", "csv",
                    "--cuc", relative_cuc, "--output", str(output),
                ]), 0)
                index.assert_called_once_with(Path(relative_cuc))
                self.assertIn(str(cuc.resolve()), output_text.getvalue())


if __name__ == "__main__":
    unittest.main()
