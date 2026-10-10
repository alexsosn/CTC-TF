"""Both CUC-attached CLI paths must keep Burns source and CUC trees immutable."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ugarit_context_parsing import cli


class ModuleV1CliOverlapTests(unittest.TestCase):
    def test_module_v1_rejects_source_and_cuc_overlap_before_index_or_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "burns-source"
            cuc_root = root / "cuc-parent" / "cuc"
            source_root.mkdir()
            cuc_root.mkdir(parents=True)
            (source_root / "sentinel.csv").write_bytes(b"licensed source bytes\n")
            (cuc_root / "sentinel.tf").write_bytes(b"base feature bytes\n")
            source = SimpleNamespace(root=source_root, records=(), files=())
            for label, output in (
                ("source_same", source_root),
                ("source_inside", source_root / "out"),
                ("source_parent", root),
                ("cuc_same", cuc_root),
                ("cuc_inside", cuc_root / "out"),
                ("cuc_parent", cuc_root.parent),
            ):
                with self.subTest(case=label), (
                    patch.object(cli, "_load_source", return_value=source),
                    patch.object(cli, "normalize_workbook_records",
                                 side_effect=AssertionError("normalization must not run")),
                    patch.object(cli, "build_reviewed_cuc_index",
                                 side_effect=AssertionError("index must not load")),
                    self.assertRaisesRegex(SystemExit, "overlaps.*directory"),
                ):
                    cli.main([
                        "module-v1", str(source_root), "--input-format", "csv",
                        "--cuc", str(cuc_root), "--output", str(output),
                    ])
            self.assertEqual(
                (source_root / "sentinel.csv").read_bytes(),
                b"licensed source bytes\n",
            )
            self.assertEqual(
                (cuc_root / "sentinel.tf").read_bytes(), b"base feature bytes\n"
            )

    def test_module_v1_rejects_alias_to_source_even_if_output_name_looks_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "actual-source"
            cuc_root = root / "actual-cuc"
            source_root.mkdir()
            cuc_root.mkdir()
            alias = root / "alias"
            try:
                alias.symlink_to(source_root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            source = SimpleNamespace(root=source_root, records=(), files=())
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "normalize_workbook_records",
                             side_effect=AssertionError("normalization must not run")),
                self.assertRaisesRegex(SystemExit, "overlaps source directory"),
            ):
                cli.main([
                    "module-v1", str(source_root), "--input-format", "csv",
                    "--cuc", str(cuc_root), "--output", str(alias / "new-module"),
                ])
            self.assertFalse((source_root / "new-module").exists())


if __name__ == "__main__":
    unittest.main()
