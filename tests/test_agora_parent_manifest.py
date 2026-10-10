"""Source-safe contract for Agora's CUC-parent Burns feature module."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "agora.materializer.json"


class AgoraBurnsManifestTests(unittest.TestCase):
    def test_parent_bound_local_only_feature_module(self):
        self.assertTrue(MANIFEST.is_file(), "Agora manifest must exist")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["plugin"]["id"], "cuc-burns")
        self.assertEqual(manifest["plugin"]["version"], "0.3.0")
        self.assertEqual(len(manifest["materializers"]), 1)
        m = manifest["materializers"][0]
        self.assertEqual(m["id"], "cuc-burns-csv")
        self.assertEqual(m["acquisition"], [{
            "type": "user-local",
            "path_type": "directory",
            "prompt": "Select a local directory of licensed Burns Workbooks CSV files; no redistribution",
        }])
        self.assertEqual(m["input"], {
            "type": "directory", "required_globs": ["*/*.csv"],
            "allow_symlinks": False,
        })
        self.assertEqual(m["parent_input"], {
            "resource": "cuc", "parent_versions": ["0.2.8"],
            "required_paths": ["otype.tf", "oslots.tf", "otext.tf"],
        })
        self.assertEqual(m["execution"], {
            "type": "python-module",
            "module": "ugarit_context_parsing.cli",
            "args": [
                "module", "{source}", "--input-format", "csv",
                "--cuc", "{parent}", "--output", "{output}",
            ],
            "network": "deny",
        })
        self.assertEqual(m["output"]["format"], "text-fabric")
        self.assertEqual(m["output"]["required_paths"], ["burns-feature-module-report.json"])
        self.assertEqual(m["output"]["composition"], {
            "kind": "feature-module", "parent": "cuc",
            "compatibility": {"parent_versions": ["0.2.8"]},
        })
        self.assertFalse(
            {"otype.tf", "oslots.tf", "otext.tf"} &
            set(m["output"]["required_paths"])
        )


if __name__ == "__main__":
    unittest.main()
