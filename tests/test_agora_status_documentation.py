from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _agora_status_section() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marker = "### Agora status\n"
    if marker not in readme:
        raise AssertionError("README has no Agora status section")
    section = readme.split(marker, 1)[1].split("\n### ", 1)[0]
    return section


class AgoraStatusDocumentationContractTests(unittest.TestCase):
    def test_current_registration_and_working_local_module_are_distinguished(self):
        section = _agora_status_section().casefold()
        self.assertIn("legacy", section)
        self.assertTrue("single-input" in section or "one-source" in section)
        self.assertIn("module", section)
        self.assertIn("public", section)
        self.assertIn("context-fabric", section)

    def test_parent_resource_support_is_open_but_explicitly_post_1_0(self):
        section = _agora_status_section().casefold()
        self.assertIn("alexsosn/agora#135", section)
        self.assertIn("open", section)
        self.assertIn("deferred", section)
        self.assertIn("after agora 1.0", section)
        self.assertNotIn("until that lands", section)

    def test_migration_tracker_and_no_fake_workaround_boundary_remain_explicit(self):
        section = _agora_status_section().casefold()
        self.assertIn("#29", section)
        self.assertIn("fake one-input", section)
        self.assertIn("copy cuc", section)
        self.assertIn("network", section)


if __name__ == "__main__":
    unittest.main()
