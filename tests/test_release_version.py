from importlib import metadata
import unittest


TARGET_VERSION = "0.3.0"


class ReleaseVersionContractTests(unittest.TestCase):
    def test_installed_package_uses_release_version(self):
        self.assertEqual(metadata.version("ugarit-context-parsing"), TARGET_VERSION)


if __name__ == "__main__":
    unittest.main()
