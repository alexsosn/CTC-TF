"""Keep the README's Agora integration claims faithful to the opt-in host.

The old contract assumed parent-aware execution did not exist. Actual Agora
PRs #238 and #240 now expose a deliberately approved, sandboxed local CLI.
Tests distinguish this from automatic discovery or Burns source acquisition.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _agora_status_section() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marker = "### Agora status\n"
    if marker not in readme:
        raise AssertionError("README has no Agora status section")
    return readme.split(marker, 1)[1].split("\n### ", 1)[0].casefold()


class AgoraStatusDocumentationContractTests(unittest.TestCase):
    def test_parent_bound_local_module_remains_feature_only(self):
        section = _agora_status_section()
        for phrase in (
            "cuc-burns", "feature-module", "parent `cuc`",
            "local-module", "agora #175", "existing cuc nodes",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)
        self.assertIn("old standalone", section)
        self.assertNotIn("legacy single-input", section)

    def test_managed_production_is_explicitly_opt_in_and_approved(self):
        section = _agora_status_section()
        for phrase in (
            "#238", "#240", "opt-in", "cuc-burns-csv",
            "python -m scripts.agora_compose_feature_module",
            "--module cuc-burns", "--source /absolute/path/to/burns-csv",
            "python scripts/agora_install_materializer.py fetch cuc-burns",
            "python scripts/agora_install_materializer.py install cuc-burns --approve-code-execution",
            "read-only cuc 0.2.8 parent", "required os sandbox",
            "network-denied",
            "cuc-burns-managed.md",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_source_license_and_warp_remain_under_explicit_boundaries(self):
        section = _agora_status_section()
        for phrase in (
            "user-local licensed", "no automatic", "source acquisition",
            "never copies", "cuc warp", "windows fails closed",
            "release tracking disabled", "v0.3.0",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)
        self.assertNotIn("automatic materialization during discovery", section)
        self.assertNotIn("implicit network fallback", section)

    def test_unfinished_general_orchestration_not_conflated_with_available_cli(self):
        section = _agora_status_section()
        self.assertIn("agora #135", section)
        self.assertIn("ticket remains open", section)
        self.assertIn("does not mean the opt-in cli is unavailable", section)



    def test_published_release_is_not_confused_with_older_agora_pin(self):
        section = _agora_status_section()
        self.assertIn("v0.3.0 was published", section)
        self.assertIn("ed6c7059803ff1adee057f5bd94d3ca661aac187", section)
        self.assertIn("f58b162197ad8f113b7cd6fc0088ae5dd39a096d", section)
        self.assertIn("release tracking disabled", section)
        self.assertNotIn("pending the separate github `v0.3.0` publication", section)

if __name__ == "__main__":
    unittest.main()
