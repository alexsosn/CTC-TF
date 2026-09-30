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
    def test_current_local_module_registration_is_described(self):
        section = _agora_status_section().casefold()
        self.assertIn("cuc-burns", section)
        self.assertIn("local-module", section)
        self.assertIn("alexsosn/agora#175", section)
        self.assertNotIn("legacy single-input", section)

    def test_managed_parent_materialization_is_tracked_post_1_0(self):
        section = _agora_status_section().casefold()
        self.assertIn("alexsosn/agora#135", section)
        self.assertIn("open", section)
        self.assertIn("managed", section)
        self.assertIn("parent", section)

    def test_no_fake_one_input_or_parent_copy_workaround_is_advertised(self):
        section = _agora_status_section().casefold()
        self.assertIn("fake one-input", section)
        self.assertIn("copy cuc", section)
        self.assertIn("network", section)


if __name__ == "__main__":
    unittest.main()
