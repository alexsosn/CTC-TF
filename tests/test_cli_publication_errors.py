from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from contextlib import ExitStack, redirect_stderr
from unittest.mock import Mock, patch

from ugarit_context_parsing import cli


MODULE_ARGS = [
    "module",
    "burns-source",
    "--input-format",
    "csv",
    "--cuc",
    "cuc/tf/0.2.8",
    "--output",
    "tf/burns-module",
]
LEGACY_ARGS = [
    "convert",
    "burns-source",
    "--input-format",
    "csv",
    "--output",
    "tf/legacy",
]


def _source():
    return SimpleNamespace(
        root=Path("burns-source").resolve(),
        files=("01/Worksheet 1.csv",),
        records=(object(),),
    )


def _module_context(*, writer_side_effect=None, writer_return=True, aligner_side_effect=None):
    source = _source()
    normalized = SimpleNamespace(records=(object(),), annotations=(object(),))
    index = object()
    alignments = (object(),)
    module = object()
    report = {"schema": "burns-tf-module-report-v1"}
    writer = Mock(return_value=writer_return, side_effect=writer_side_effect)
    aligner = Mock(return_value=alignments, side_effect=aligner_side_effect)
    return (
        writer,
        aligner,
        patch.object(cli, "load_csv_directory", return_value=source),
        patch.object(cli, "normalize_workbook_records", return_value=normalized),
        patch.object(cli, "build_reviewed_cuc_index", return_value=index),
        patch.object(cli, "align_burns_source", aligner),
        patch.object(cli, "build_burns_module", return_value=module),
        patch.object(cli, "build_burns_module_report", return_value=report),
        patch.object(cli, "write_burns_module", writer),
    )


def _legacy_context(*, writer_side_effect=None, writer_return=True):
    source = _source()
    data = object()
    report = {"status": "ok"}
    writer = Mock(return_value=writer_return, side_effect=writer_side_effect)
    return (
        writer,
        patch.object(cli, "load_csv_directory", return_value=source),
        patch.object(cli, "build_tf_data", return_value=data),
        patch.object(cli, "build_conversion_report", return_value=report),
        patch.object(cli, "write_artifact", writer),
    )


class CliPublicationErrorTests(unittest.TestCase):
    def _assert_module_writer_exception(self, error: Exception) -> None:
        writer, _, *patchers = _module_context(writer_side_effect=error)
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            with self.assertRaisesRegex(
                SystemExit,
                rf"^module publication failed: {error}$",
            ):
                cli.main(MODULE_ARGS)
        writer.assert_called_once()

    def _assert_legacy_writer_exception(self, error: Exception) -> None:
        writer, *patchers = _legacy_context(writer_side_effect=error)
        stderr = io.StringIO()
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            stack.enter_context(redirect_stderr(stderr))
            with self.assertRaisesRegex(
                SystemExit,
                rf"^legacy publication failed: {error}$",
            ):
                cli.main(LEGACY_ARGS)
        writer.assert_called_once()
        self.assertEqual(stderr.getvalue(), cli.LEGACY_CONVERT_WARNING + "\n")

    def test_module_value_error_becomes_publication_diagnostic(self):
        self._assert_module_writer_exception(ValueError("unsafe output"))

    def test_module_runtime_error_becomes_publication_diagnostic(self):
        self._assert_module_writer_exception(RuntimeError("invalid staged TF inventory"))

    def test_module_os_error_becomes_publication_diagnostic(self):
        self._assert_module_writer_exception(OSError("read-only filesystem"))

    def test_legacy_value_error_becomes_publication_diagnostic(self):
        self._assert_legacy_writer_exception(ValueError("unsafe output"))

    def test_legacy_runtime_error_becomes_publication_diagnostic(self):
        self._assert_legacy_writer_exception(RuntimeError("missing staged TF files"))

    def test_legacy_os_error_becomes_publication_diagnostic(self):
        self._assert_legacy_writer_exception(OSError("read-only filesystem"))

    def test_module_false_return_message_is_unchanged(self):
        writer, _, *patchers = _module_context(writer_return=False)
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            with self.assertRaisesRegex(
                SystemExit,
                r"^Text-Fabric refused the generated Burns module$",
            ):
                cli.main(MODULE_ARGS)
        writer.assert_called_once()

    def test_legacy_false_return_message_is_unchanged(self):
        writer, *patchers = _legacy_context(writer_return=False)
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            stack.enter_context(redirect_stderr(io.StringIO()))
            with self.assertRaisesRegex(
                SystemExit,
                r"^Text-Fabric refused the generated dataset$",
            ):
                cli.main(LEGACY_ARGS)
        writer.assert_called_once()

    def test_prepublication_alignment_value_error_is_not_swallowed(self):
        writer, aligner, *patchers = _module_context(
            aligner_side_effect=ValueError("alignment invariant failed")
        )
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            with self.assertRaisesRegex(ValueError, "alignment invariant failed"):
                cli.main(MODULE_ARGS)
        aligner.assert_called_once()
        writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
