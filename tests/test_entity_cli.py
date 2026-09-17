"""#68: the queryable product must be reachable through a public CLI command."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout

from ugarit_context_parsing import cli


class EntityCliTests(unittest.TestCase):
    def test_help_exposes_explicit_native_entity_command_without_silently_changing_v1(self):
        text = cli._parser().format_help()
        self.assertIn("entities", text)
        self.assertIn("module", text)

    def test_entities_routes_validated_source_reviewed_cuc_and_loaded_warp_to_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source"
            source_path.mkdir()
            cuc = root / "cuc"
            cuc.mkdir()
            output = root / "native"
            source = SimpleNamespace(root=source_path, records=("raw",), files=("01.csv",))
            api = object()
            fake_fabric = SimpleNamespace(loadAll=lambda **kwargs: api)
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "normalize_workbook_records", return_value=SimpleNamespace(records=(1,), annotations=(1,))),
                patch.object(cli, "build_reviewed_cuc_index", return_value="reviewed-index"),
                patch.object(cli, "align_burns_source", return_value=("alignment",)),
                patch("tf.fabric.Fabric", return_value=fake_fabric) as fabric,
                patch("ugarit_context_parsing.entity_writer.write_entity_artifact", return_value=True) as writer,
                redirect_stdout(io.StringIO()) as output_text,
            ):
                self.assertEqual(cli.main(["entities", str(source_path), "--input-format", "csv", "--cuc", str(cuc), "--output", str(output)]), 0)
                fabric.assert_called_once()
                writer.assert_called_once()
                args = writer.call_args.args
                self.assertEqual(args[2], "reviewed-index")
                self.assertIs(args[3], api)
                self.assertEqual(args[4], output)
                self.assertIn("native Burns", output_text.getvalue())

    def test_entities_rejects_source_or_cuc_output_overlap_before_loading_base(self):
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
                        cli.main(["entities", str(source_path), "--input-format", "csv", "--cuc", str(cuc), "--output", str(output)])
                index.assert_not_called()


if __name__ == "__main__":
    unittest.main()
