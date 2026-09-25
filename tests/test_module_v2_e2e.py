"""Default public CLI integration: a real Fabric output, not a mocked router.

Uses synthetic source and CUC, NOT a real Burns source coverage audit. The
separate reviewed-CUC workflow exercises the pinned CUC and MCP consumer.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tf.fabric import Fabric

from test_burns_entity_extension import _write_indexed_base
from test_burns_tf_module import _index, _record
from ugarit_context_parsing import cli


class ModuleV2EndToEndTests(unittest.TestCase):
    def test_primary_module_writes_v2_warp_and_native_query_with_no_json_features(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "cuc"
            _write_indexed_base(base)
            source_root = root / "workbooks"
            source_root.mkdir()
            source = SimpleNamespace(
                root=source_root,
                files=("01 Synthetic/Worksheet 1.csv",),
                records=(_record(1, headword="bʿl", references="I.2"),),
            )
            output = root / "burns-v2"
            with (
                patch.object(cli, "_load_source", return_value=source),
                patch.object(cli, "build_reviewed_cuc_index", return_value=_index()),
            ):
                self.assertEqual(cli.main([
                    "module", str(source_root), "--input-format", "csv",
                    "--cuc", str(base), "--output", str(output),
                ]), 0)
            inventory = {entry.name for entry in output.iterdir()}
            self.assertIn("otype.tf", inventory)
            self.assertIn("oslots.tf", inventory)
            self.assertIn("burns_category.tf", inventory)
            self.assertIn("burns_headword.tf", inventory)
            self.assertIn("burns-entity-report.json", inventory)
            self.assertFalse({
                "burns_annotations.tf", "burns_annotation_ids.tf",
                "burns_headwords.tf", "burns_worksheet_roles.tf",
                "burns_semantic_statuses.tf", "burns_sections.tf",
            } & inventory)
            report = json.loads((output / "burns-entity-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "burns-entity-module-v2")
            self.assertEqual(report["counts"]["native_entities"], 1)
            self.assertEqual(len(report["source_records"]), 1)
            combined = Fabric(
                locations=[str(base), str(output)], modules=[""], silent="deep"
            ).loadAll(silent="deep")
            self.assertIsNotNone(combined)
            assert combined is not None
            hits = tuple(combined.S.search(
                "entity burns_headword=bʿl burns_category=divine_name", silent="deep"
            ))
            self.assertEqual(len(hits), 1)
            self.assertEqual(combined.F.otype.v(hits[0][0]), "entity")
            self.assertEqual(tuple(combined.L.d(hits[0][0], otype="word")), (8,))
            self.assertIsNone(combined.F.burns_headword.v(8))
            self.assertNotIn("burns_annotations", combined.Fall())
            # Explicit version migration is non-destructive: never replace an
            # existing output, even a clean artifact from the prior invocation.
            with (
                patch.object(cli, "_load_source", return_value=source),
                self.assertRaisesRegex(SystemExit, "refusing to overwrite"),
            ):
                cli.main([
                    "module", str(source_root), "--input-format", "csv",
                    "--cuc", str(base), "--output", str(output),
                ])


if __name__ == "__main__":
    unittest.main()
