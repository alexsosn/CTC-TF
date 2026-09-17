"""Independent review regression: no unowned regular directories in staging."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_entity_writer import BurnsEntityWriterTests
from ugarit_context_parsing.entity_writer import write_entity_artifact


class _ExtraDirectoryFabric:
    def __init__(self, **kwargs):
        self._fabric = Fabric(**kwargs)

    def save(self, **kwargs):
        saved = self._fabric.save(**kwargs)
        if saved:
            (Path(kwargs["location"]) / "foreign-directory").mkdir()
        return saved


class EntityPublisherAdversarialTests(unittest.TestCase):
    def test_unexpected_staged_directory_is_rejected_and_no_output_is_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, source, alignments, index, api = BurnsEntityWriterTests()._inputs(root)
            output = root / "native"
            with self.assertRaises(RuntimeError):
                write_entity_artifact(
                    source, alignments, index, api, output,
                    fabric_factory=_ExtraDirectoryFabric,
                )
            self.assertFalse(output.exists())
            self.assertEqual(
                sorted(path.name for path in root.iterdir()), ["cuc"],
                "a failed publish must clean its staging directory",
            )


if __name__ == "__main__":
    unittest.main()
