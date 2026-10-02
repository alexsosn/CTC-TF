"""Default public CLI integration for the corrected feature-only Burns module."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tf.fabric import Fabric

from test_burns_tf_module import _index, _record, _write_synthetic_base
from ugarit_context_parsing import cli
from ugarit_context_parsing.feature_module import REPORT_FILE, SCHEMA


class ModuleV2EndToEndTests(unittest.TestCase):
    def test_primary_module_writes_feature_only_overlay_and_native_query(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "cuc"
            _write_synthetic_base(base)
            source_root = root / "workbooks"
            source_root.mkdir()
            source = SimpleNamespace(
                root=source_root,
                files=("01 Synthetic/Worksheet 1.csv",),
                records=(_record(1, headword="bʿl", references="I.2"),),
            )
            output = root / "burns-feature"
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "build_reviewed_cuc_index", return_value=_index()),
            ):
                self.assertEqual(cli.main([
                    "module", str(source_root), "--input-format", "csv",
                    "--cuc", str(base), "--output", str(output),
                ]), 0)

            inventory = {entry.name for entry in output.iterdir()}
            self.assertNotIn("otype.tf", inventory)
            self.assertNotIn("oslots.tf", inventory)
            self.assertNotIn("otext.tf", inventory)
            self.assertIn("burns_category_1.tf", inventory)
            self.assertIn("burns_headword_1.tf", inventory)
            self.assertIn("burns_span_length_1.tf", inventory)
            self.assertIn(REPORT_FILE, inventory)
            self.assertFalse({
                "burns_annotations.tf", "burns_annotation_ids.tf",
                "burns_headwords.tf", "burns_worksheet_roles.tf",
                "burns_semantic_statuses.tf", "burns_sections.tf",
            } & inventory)

            report = json.loads((output / REPORT_FILE).read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], SCHEMA)
            self.assertEqual(report["counts"]["exact_lexical_occurrences"], 1)
            self.assertEqual(report["counts"]["max_lane"], 1)
            self.assertEqual(len(report["source_records"]), 1)

            original = Fabric(
                locations=[str(base)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            combined = Fabric(
                locations=[str(base), str(output)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            self.assertIsNotNone(original)
            self.assertIsNotNone(combined)
            assert original is not None and combined is not None
            self.assertEqual(combined.F.otype.maxSlot, original.F.otype.maxSlot)
            self.assertEqual(combined.F.otype.maxNode, original.F.otype.maxNode)
            self.assertEqual(tuple(combined.F.otype.s("entity")), ())
            self.assertEqual(
                tuple(combined.S.search(
                    "word burns_headword_1=bʿl burns_category_1=divine_name",
                    silent="deep",
                )),
                ((8,),),
            )
            self.assertEqual(combined.F.burns_span_length_1.v(8), 1)
            self.assertIsNone(combined.F.burns_headword_1.v(13))

            # Version migration is non-destructive: never replace an existing output.
            with (
                patch.object(cli, "_load_source", return_value=source),
                self.assertRaisesRegex(SystemExit, "refusing to overwrite|already exists"),
            ):
                cli.main([
                    "module", str(source_root), "--input-format", "csv",
                    "--cuc", str(base), "--output", str(output),
                ])


if __name__ == "__main__":
    unittest.main()
