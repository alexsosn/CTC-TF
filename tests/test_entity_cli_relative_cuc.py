"""Regression: the native CLI must support a relative --cuc path.

The reviewed index builder resolves a relative path after fingerprinting it;
Fabric must load the same absolute directory rather than interpreting a
relative location through Text-Fabric's module discovery logic.
"""
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


class EntityRelativeCucPathTests(unittest.TestCase):
    def test_relative_reviewed_cuc_is_loaded_from_exact_absolute_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source"
            source_path.mkdir()
            cuc = root / "cuc"
            cuc.mkdir()
            output = root / "native"
            relative_cuc = os.path.relpath(cuc, Path.cwd())
            source = SimpleNamespace(root=source_path, records=("raw",), files=("01.csv",))
            api = object()
            fake_fabric = SimpleNamespace(loadAll=lambda **kwargs: api)
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "normalize_workbook_records", return_value=SimpleNamespace(records=(1,), annotations=(1,))),
                patch.object(cli, "build_reviewed_cuc_index", return_value="reviewed-index") as index,
                patch.object(cli, "align_burns_source", return_value=("alignment",)),
                patch("tf.fabric.Fabric", return_value=fake_fabric) as fabric,
                patch("ugarit_context_parsing.entity_writer.write_entity_artifact", return_value=True) as writer,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(cli.main([
                    "entities", str(source_path), "--input-format", "csv",
                    "--cuc", relative_cuc, "--output", str(output),
                ]), 0)
                index.assert_called_once_with(Path(relative_cuc))
                fabric.assert_called_once_with(
                    locations=[str(cuc.resolve())], modules=[""], silent="deep"
                )
                self.assertIs(writer.call_args.args[3], api)


if __name__ == "__main__":
    unittest.main()
