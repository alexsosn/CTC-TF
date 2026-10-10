from importlib import metadata
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.3.0"
class ReleaseVersionContractTests(unittest.TestCase):
    def test_installed_package_uses_release_version(self):
        self.assertEqual(metadata.version("ugarit-context-parsing"), TARGET_VERSION)

    def test_release_notes_describe_feature_only_primary_product(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        self.assertIn("feature-only", notes)
        self.assertIn("module-v1", notes)
        self.assertIn("no `otype.tf`", notes)
        self.assertNotIn("otype=entity", notes)

    def test_release_notes_preserve_distribution_boundaries(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        self.assertNotIn("standalone `convert` command is retained", notes)
        self.assertNotIn("burns-workbooks-csv-text-fabric", notes)
        self.assertNotIn("burns-workbooks-pdf-text-fabric", notes)
        # The frozen v0.3.0 release remains feature-only; a later parent-bound\n        # Agora manifest is allowed only when its source and output contracts\n        # are separately verified by test_agora_parent_manifest.py.\n        self.assertNotIn("burns-workbooks-csv-text-fabric", notes)
        self.assertIn("No Burns-derived data files are attached", notes)
        self.assertIn("Agora", notes)


if __name__ == "__main__":
    unittest.main()
