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

    def test_release_notes_describe_actual_agora_parent_bound_adapter_and_frozen_evidence(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        for evidence in (
            "agora.materializer.json",
            "cuc-burns-csv",
            "ugarit_context_parsing.agora_adapter",
            "0408967b1808c1f22c69e299d302b1e7b5e26354",
            "45 Workbooks",
            "5,909",
            "Bubblewrap",
            "pre-created empty",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, notes)
        self.assertIn("No Burns-derived data files are attached", notes)
        self.assertIn("not yet published", notes)
        self.assertIn("not yet registered", notes)
        self.assertNotIn("fully managed source+parent materializer execution remains", notes.lower())

    def test_release_manifest_and_project_metadata_agree_without_legacy_conversion(self):
        import json
        import re

        # Python 3.10 is in the release matrix; stdlib tomllib exists only
        # from Python 3.11. Scope the version extraction to [project].
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        project_section = pyproject.split("[project]", 1)[1].split("\n[", 1)[0]
        version = re.search(r'^version\s*=\s*"([^"]+)"', project_section, re.MULTILINE)
        self.assertIsNotNone(version)
        manifest = json.loads((ROOT / "agora.materializer.json").read_text(encoding="utf-8"))
        self.assertEqual(version.group(1), TARGET_VERSION)
        self.assertEqual(manifest["plugin"]["version"], TARGET_VERSION)
        materializer = manifest["materializers"][0]
        self.assertEqual(materializer["id"], "cuc-burns-csv")
        self.assertEqual(materializer["execution"]["module"], "ugarit_context_parsing.agora_adapter")
        self.assertEqual(materializer["parent_input"]["resource"], "cuc")
        self.assertEqual(materializer["output"]["composition"]["kind"], "feature-module")
        self.assertNotIn("convert", " ".join(materializer["execution"]["args"]))
        self.assertEqual(materializer["acquisition"][0]["type"], "user-local")

    def test_release_notes_preserve_distribution_boundaries(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
        self.assertNotIn("standalone `convert` command is retained", notes)
        self.assertNotIn("burns-workbooks-csv-text-fabric", notes)
        self.assertNotIn("burns-workbooks-pdf-text-fabric", notes)
        # A later parent-bound Agora manifest does not restore the old
        # standalone materializer or alter frozen release notes.
        self.assertIn("No Burns-derived data files are attached", notes)
        self.assertIn("Agora", notes)


if __name__ == "__main__":
    unittest.main()
