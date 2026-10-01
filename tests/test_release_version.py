from importlib import metadata
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.3.0"


class ReleaseVersionContractTests(unittest.TestCase):
    def test_installed_package_uses_release_version(self):
        self.assertEqual(metadata.version("ugarit-context-parsing"), TARGET_VERSION)

    def test_legacy_agora_materializer_manifest_is_not_shipped(self):
        self.assertFalse(
            (ROOT / "agora.materializer.json").exists(),
            "standalone convert manifest must stay removed",
        )


if __name__ == "__main__":
    unittest.main()
