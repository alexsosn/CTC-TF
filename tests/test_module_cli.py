from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ugarit_context_parsing import cli
from ugarit_context_parsing.cuc_index import CucCompatibilityError


LEGACY_WARNING = (
    "deprecated: 'convert' creates the legacy standalone Burns row-slot corpus; "
    "use 'module' for the CUC-aligned feature module\n"
)


class ModuleCliTests(unittest.TestCase):
    def test_help_exposes_native_primary_and_explicit_legacy_commands(self) -> None:
        help_text = cli._parser().format_help()
        self.assertIn("module", help_text)
        self.assertIn("module-v1", help_text)
        self.assertIn("CUC-aligned", help_text)
        self.assertIn("deprecated", help_text.lower())

    def test_module_command_requires_cuc_and_preserves_paths(self) -> None:
        parser = cli._parser()
        args = parser.parse_args([
            "module", "burns-source", "--input-format", "csv",
            "--cuc", "cuc/tf/0.2.8", "--output", "tf/burns-module",
        ])
        self.assertEqual(args.command, "module")
        self.assertEqual(args.source, Path("burns-source"))
        self.assertEqual(args.cuc, Path("cuc/tf/0.2.8"))
        self.assertEqual(args.output, Path("tf/burns-module"))
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "module", "burns-source", "--input-format", "csv",
                "--output", "tf/burns-module",
            ])

    def test_csv_v1_compatibility_routes_through_reviewed_pipeline_and_v1_writer(self) -> None:
        source = SimpleNamespace(files=("01/Worksheet 1.csv",), records=(object(),))
        normalized = SimpleNamespace(records=(object(),), annotations=(object(), object()))
        index = object()
        alignments = (object(), object())
        module = object()
        report = {"schema": "burns-tf-module-report-v1"}
        loader = Mock(return_value=source)
        normalizer = Mock(return_value=normalized)
        indexer = Mock(return_value=index)
        aligner = Mock(return_value=alignments)
        builder = Mock(return_value=module)
        reporter = Mock(return_value=report)
        writer = Mock(return_value=True)
        with (
            patch.object(cli, "load_csv_directory", loader),
            patch.object(cli, "normalize_workbook_records", normalizer),
            patch.object(cli, "build_reviewed_cuc_index", indexer),
            patch.object(cli, "align_burns_source", aligner),
            patch.object(cli, "build_burns_module", builder),
            patch.object(cli, "build_burns_module_report", reporter),
            patch.object(cli, "write_burns_module", writer),
            patch.object(cli, "build_tf_data") as standalone_builder,
            patch.object(cli, "write_artifact") as standalone_writer,
            redirect_stdout(io.StringIO()),
        ):
            result = cli.main([
                "module-v1", "burns-source", "--input-format", "csv",
                "--cuc", "cuc/tf/0.2.8", "--output", "tf/burns-module",
            ])
        self.assertEqual(result, 0)
        loader.assert_called_once_with(Path("burns-source"))
        normalizer.assert_called_once_with(source.records)
        indexer.assert_called_once_with(Path("cuc/tf/0.2.8"))
        aligner.assert_called_once_with(normalized, index)
        builder.assert_called_once_with(normalized, alignments, index)
        reporter.assert_called_once_with(normalized, alignments, index, module)
        writer.assert_called_once_with(module, report, Path("tf/burns-module"))
        standalone_builder.assert_not_called()
        standalone_writer.assert_not_called()

    def test_pdf_v1_compatibility_uses_pdf_loader_and_v1_writer(self) -> None:
        source = SimpleNamespace(files=("01/Worksheet 1.pdf",), records=(object(),))
        normalized = SimpleNamespace(records=(object(),), annotations=(object(),))
        index, alignments, module = object(), (object(),), object()
        report = {"schema": "burns-tf-module-report-v1"}
        csv_loader = Mock()
        pdf_loader = Mock(return_value=source)
        normalizer = Mock(return_value=normalized)
        indexer = Mock(return_value=index)
        aligner = Mock(return_value=alignments)
        builder = Mock(return_value=module)
        reporter = Mock(return_value=report)
        writer = Mock(return_value=True)
        with (
            patch.object(cli, "load_csv_directory", csv_loader),
            patch.object(cli, "load_pdf_directory", pdf_loader),
            patch.object(cli, "normalize_workbook_records", normalizer),
            patch.object(cli, "build_reviewed_cuc_index", indexer),
            patch.object(cli, "align_burns_source", aligner),
            patch.object(cli, "build_burns_module", builder),
            patch.object(cli, "build_burns_module_report", reporter),
            patch.object(cli, "write_burns_module", writer),
            redirect_stdout(io.StringIO()),
        ):
            result = cli.main([
                "module-v1", "burns-source", "--input-format", "pdf",
                "--cuc", "cuc/tf/0.2.8", "--output", "tf/burns-module",
            ])
        self.assertEqual(result, 0)
        csv_loader.assert_not_called()
        pdf_loader.assert_called_once_with(Path("burns-source"))
        normalizer.assert_called_once_with(source.records)
        indexer.assert_called_once_with(Path("cuc/tf/0.2.8"))
        writer.assert_called_once_with(module, report, Path("tf/burns-module"))

    def test_invalid_cuc_fails_before_v1_publication(self) -> None:
        source = SimpleNamespace(files=("01/Worksheet 1.csv",), records=(object(),))
        normalized = SimpleNamespace(records=(object(),), annotations=(object(),))
        writer = Mock()
        with (
            patch.object(cli, "load_csv_directory", return_value=source),
            patch.object(cli, "normalize_workbook_records", return_value=normalized),
            patch.object(cli, "build_reviewed_cuc_index", side_effect=CucCompatibilityError("fingerprint mismatch")),
            patch.object(cli, "write_burns_module", writer),
            self.assertRaisesRegex(SystemExit, r"^CUC validation failed: fingerprint mismatch$"),
        ):
            cli.main([
                "module-v1", "burns-source", "--input-format", "csv",
                "--cuc", "wrong-cuc", "--output", "tf/burns-module",
            ])
        writer.assert_not_called()

    def test_legacy_convert_still_runs_with_visible_deprecation(self) -> None:
        source = SimpleNamespace(files=("01/Worksheet 1.csv",), records=(object(),))
        data = object()
        report = {"status": "ok"}
        stderr = io.StringIO()
        with (
            patch.object(cli, "load_csv_directory", return_value=source),
            patch.object(cli, "build_tf_data", return_value=data),
            patch.object(cli, "build_conversion_report", return_value=report),
            patch.object(cli, "write_artifact", return_value=True),
            redirect_stderr(stderr),
            redirect_stdout(io.StringIO()),
        ):
            result = cli.main([
                "convert", "burns-source", "--input-format", "csv",
                "--output", "tf/legacy",
            ])
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), LEGACY_WARNING)


if __name__ == "__main__":
    unittest.main()
