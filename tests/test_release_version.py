from importlib import metadata
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.3.0"
EXPECTED_MATERIALIZERS = [
    "burns-workbooks-csv-text-fabric",
    "burns-workbooks-pdf-text-fabric",
]


class ReleaseVersionContractTests(unittest.TestCase):
    def test_installed_package_uses_release_version(self):
        self.assertEqual(metadata.version("ugarit-context-parsing"), TARGET_VERSION)

    def test_materializer_manifest_uses_same_release_version_and_identity(self):
        manifest = json.loads((ROOT / "agora.materializer.json").read_text(encoding="utf-8"))
        plugin = manifest["plugin"]
        self.assertEqual(plugin["version"], TARGET_VERSION)
        self.assertEqual(plugin["id"], "ugarit-context-parsing")
        self.assertEqual(plugin["repository"], "alexsosn/ugarit-context-parsing")
        self.assertEqual(
            [entry["id"] for entry in manifest["materializers"]],
            EXPECTED_MATERIALIZERS,
        )


    def test_release_notes_describe_native_v2_primary_product(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        self.assertIn("otype=entity", notes)
        self.assertIn("module-v1", notes)
        self.assertNotIn("feature-only Text-Fabric module", notes)

    def test_release_notes_preserve_distribution_boundaries(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        self.assertIn("convert", notes)
        self.assertIn("No Burns-derived data files are attached", notes)
        self.assertIn("Agora", notes)


if __name__ == "__main__":
    unittest.main()
