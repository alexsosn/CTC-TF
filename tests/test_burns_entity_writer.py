"""#68: first public writer gate; never replace unknown files or publish blobs."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_entity_extension import _write_indexed_base
from test_burns_tf_module import _index, _source
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.entity_writer import write_entity_artifact


class _RefuseFabric:
    def __init__(self, **kwargs):
        pass

    def save(self, **kwargs):
        return False


class BurnsEntityWriterTests(unittest.TestCase):
    def _inputs(self, root):
        base = root / "cuc"
        _write_indexed_base(base)
        api = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
        self.assertIsNotNone(api)
        source = _source()
        index = _index()
        return base, source, align_burns_source(source, index), index, api

    def test_writer_publishes_native_entities_and_local_provenance_only_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, source, alignments, index, api = self._inputs(root)
            output = root / "burns-native"
            self.assertTrue(write_entity_artifact(source, alignments, index, api, output))
            self.assertTrue((output / "otype.tf").is_file())
            self.assertTrue((output / "oslots.tf").is_file())
            self.assertFalse((output / "burns_annotations.tf").exists())
            report = json.loads((output / "burns-entity-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "burns-entity-module-v2")
            self.assertEqual(len(report["entity_occurrences"]), 5)
            self.assertEqual(len(report["source_records"]), len(source.records))
            combined = Fabric(locations=[str(base), str(output)], modules=[""], silent="deep").loadAll(silent="deep")
            self.assertIsNotNone(combined)
            self.assertEqual(len(combined.S.search("entity burns_category=divine_name", silent="deep")), 5)
            self.assertEqual(len(combined.S.search("entity burns_headword=bʿl", silent="deep")), 1)
            self.assertIsNone(combined.F.burns_headword.v(8))
            self.assertEqual(combined.F.otype.maxSlot, api.F.otype.maxSlot)
            self.assertEqual(combined.F.otype.maxNode, api.F.otype.maxNode + 5)

    def test_existing_path_even_if_empty_is_never_replaced_without_ownership_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, source, alignments, index, api = self._inputs(root)
            output = root / "existing"
            output.mkdir()
            marker = output / "foreign.txt"
            marker.write_text("user data", encoding="utf-8")
            with self.assertRaises(ValueError):
                write_entity_artifact(source, alignments, index, api, output)
            self.assertEqual(marker.read_text(encoding="utf-8"), "user data")
            output2 = root / "empty"
            output2.mkdir()
            with self.assertRaises(ValueError):
                write_entity_artifact(source, alignments, index, api, output2)

    def test_refused_tf_save_never_creates_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, source, alignments, index, api = self._inputs(root)
            output = root / "failed"
            self.assertFalse(write_entity_artifact(
                source, alignments, index, api, output, fabric_factory=_RefuseFabric
            ))
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
