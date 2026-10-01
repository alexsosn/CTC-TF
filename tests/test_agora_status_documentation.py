from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _agora_status_section() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marker = "### Agora status\n"
    if marker not in readme:
        raise AssertionError("README has no Agora status section")
    return readme.split(marker, 1)[1].split("\n### ", 1)[0]


class AgoraStatusDocumentationContractTests(unittest.TestCase):
    def test_current_cuc_burns_registration_is_documented(self):
        section = _agora_status_section().casefold()
        self.assertIn("agora v1.0.0", section)
        self.assertIn("#175", section)
        self.assertIn("cuc-burns", section)
        self.assertIn("feature-module", section)
        self.assertIn("cuc", section)

    def test_managed_materialization_remains_explicitly_separate(self):
        section = _agora_status_section().casefold()
        self.assertIn("alexsosn/agora#135", section)
        self.assertIn("open", section)
        self.assertIn("managed", section)
        self.assertIn("parent", section)

    def test_removed_standalone_registration_is_not_advertised(self):
        section = _agora_status_section().casefold()
        self.assertNotIn("burns-workbooks-csv-text-fabric", section)
        self.assertNotIn("burns-workbooks-pdf-text-fabric", section)
        self.assertNotIn("legacy single-input", section)
        self.assertNotIn("agora.materializer.json", section)


if __name__ == "__main__":
    unittest.main()
