import ast
from importlib import metadata
import re
from pathlib import Path
import unittest

from ugarit_context_parsing.cuc_index import REVIEWED_CUC_COMMIT


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.3.1"


class PythonSupportContractTests(unittest.TestCase):
    def test_package_rejects_retired_python_baseline(self):
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        section = project.split("[project]", 1)[1].split("\n[", 1)[0]
        self.assertRegex(section, r'(?m)^requires-python\s*=\s*">=3\.12"$')

    def test_ci_exercises_current_python_and_local_default(self):
        workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(
            encoding="utf-8"
        )
        matrix = re.search(r"(?m)^\s+python-version:\s*(\[[^\n]+\])", workflow)
        self.assertIsNotNone(matrix)
        versions = ast.literal_eval(matrix.group(1))
        self.assertEqual(versions, ["3.12", "3.13", "3.14", "3.15"])
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.14")


class ReleaseVersionContractTests(unittest.TestCase):
    def test_installed_package_uses_release_version(self):
        self.assertEqual(metadata.version("ugarit-context-parsing"), TARGET_VERSION)

    def test_release_notes_describe_feature_only_primary_product(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.1.md").read_text(encoding="utf-8")
        self.assertIn("feature-only", notes)
        self.assertIn("module-v1", notes)
        self.assertIn("no `otype.tf`", notes)
        self.assertNotIn("otype=entity", notes)

    def test_release_notes_describe_actual_agora_parent_bound_adapter_and_frozen_evidence(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.1.md").read_text(encoding="utf-8")
        for evidence in (
            "agora.materializer.json",
            "cuc-burns-csv",
            "ugarit_context_parsing.agora_adapter",
            REVIEWED_CUC_COMMIT,
            "45 Workbooks",
            "5,909",
            "Bubblewrap",
            "pre-created empty",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, notes)
        self.assertIn("No Burns-derived data files are attached", notes)
        self.assertNotIn("0408967b1808c1f22c69e299d302b1e7b5e26354", notes)
        self.assertIn("separate distribution actions", notes)
        self.assertIn("does not by itself register", notes)
        self.assertNotIn("not yet published", notes)
        self.assertNotIn("not yet registered", notes)
        self.assertNotIn("fully managed source+parent materializer execution remains", notes.lower())

    def test_citation_version_matches_candidate_without_an_invented_release_date(self):
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn('version: "0.3.1"', citation)
        self.assertNotIn('date-released: "2026-10-12"', citation)
        self.assertIn("Cite Burns's thesis", citation)

    def test_release_pdf_quickstart_uses_single_shell_line_continuations(self):
        notes = (ROOT / "docs" / "releases" / "v0.3.1.md").read_text(encoding="utf-8")
        commands = notes.split("```sh", 1)[1].split("```", 1)[0]
        continuations = [line for line in commands.splitlines() if line.endswith("\\")]
        self.assertEqual(len(continuations), 2)
        self.assertTrue(all(not line.endswith("\\\\") for line in continuations))

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
        notes = (ROOT / "docs" / "releases" / "v0.3.1.md").read_text(encoding="utf-8")
        self.assertNotIn("standalone `convert` command is retained", notes)
        self.assertNotIn("burns-workbooks-csv-text-fabric", notes)
        self.assertNotIn("burns-workbooks-pdf-text-fabric", notes)
        # A later parent-bound Agora manifest does not restore the old
        # standalone materializer or alter frozen release notes.
        self.assertIn("No Burns-derived data files are attached", notes)
        self.assertIn("Agora", notes)


if __name__ == "__main__":
    unittest.main()
