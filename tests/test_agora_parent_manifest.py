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
            "module": "ugarit_context_parsing.agora_adapter",
            "args": [
                "{source}", "--input-format", "csv",
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


    def test_agora_adapter_fills_precreated_empty_staging_output_only(self):
        # Actual Agora _create_staging_output creates the final {output}
        # directory *before* invoking a third-party producer.
        import tempfile
        from unittest import mock
        from ugarit_context_parsing import agora_adapter

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "workbooks"
            parent = root / "cuc"
            source.mkdir()
            parent.mkdir()
            output = root / "already-created-by-agora"
            output.mkdir()

            def native(args):
                self.assertEqual(args[:2], ["module", str(source)])
                self.assertEqual(args[args.index("--cuc") + 1], str(parent))
                nested = Path(args[args.index("--output") + 1])
                self.assertFalse(nested.exists(), "native writer needs an absent path")
                self.assertEqual(nested.parent, output)
                nested.mkdir()
                (nested / "burns_headword_1.tf").write_text("feature")
                (nested / "burns-feature-module-report.json").write_text("{}")
                return 0

            with mock.patch.object(agora_adapter, "native_main", side_effect=native) as invoke:
                self.assertEqual(
                    agora_adapter.main([
                        str(source), "--input-format", "csv",
                        "--cuc", str(parent), "--output", str(output),
                    ]),
                    0,
                )
            invoke.assert_called_once()
            self.assertEqual(
                {p.name for p in output.iterdir()},
                {"burns_headword_1.tf", "burns-feature-module-report.json"},
            )

    def test_agora_adapter_fails_closed_on_absent_occupied_or_symlinked_output(self):
        import tempfile
        from unittest import mock
        from ugarit_context_parsing import agora_adapter

        for variant in ("absent", "occupied", "symlink"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source, parent = root / "workbooks", root / "cuc"
                source.mkdir()
                parent.mkdir()
                output = root / "publish"
                if variant == "occupied":
                    output.mkdir()
                    (output / "foreign.tf").write_text("do not clobber")
                if variant == "symlink":
                    outside = root / "outside"
                    outside.mkdir()
                    output.symlink_to(outside, target_is_directory=True)
                with mock.patch.object(agora_adapter, "native_main") as invoke:
                    with self.assertRaises((ValueError, SystemExit)):
                        agora_adapter.main([
                            str(source), "--input-format", "csv",
                            "--cuc", str(parent), "--output", str(output),
                        ])
                    invoke.assert_not_called()
                if variant == "occupied":
                    self.assertEqual((output / "foreign.tf").read_text(), "do not clobber")

    def test_agora_adapter_refuses_warp_and_symlink_smuggling(self):
        import tempfile
        from unittest import mock
        from ugarit_context_parsing import agora_adapter

        for bad in ("otype.tf", "oslots.tf", "otext.tf", "malicious-link"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source, parent = root / "workbooks", root / "cuc"
                source.mkdir()
                parent.mkdir()
                output = root / "staging"
                output.mkdir()

                def native(args):
                    nested = Path(args[args.index("--output") + 1])
                    nested.mkdir()
                    (nested / "burns_headword_1.tf").write_text("ok")
                    (nested / "burns-feature-module-report.json").write_text("{}")
                    if bad == "malicious-link":
                        (nested / bad).symlink_to(root)
                    else:
                        (nested / bad).write_text("forbidden")
                    return 0

                with mock.patch.object(agora_adapter, "native_main", side_effect=native):
                    with self.assertRaises((ValueError, SystemExit)):
                        agora_adapter.main([
                            str(source), "--input-format", "csv",
                            "--cuc", str(parent), "--output", str(output),
                        ])
                self.assertFalse((output / "burns_headword_1.tf").exists())

    def test_agora_host_parent_is_outside_writable_output_ancestor(self):
        # Agora intentionally refuses to mount a trusted parent beneath the
        # writable materializer output parent. $RUNNER_TEMP must not contain
        # both the trusted CUC corpus and the host's output directory.
        workflow = (
            ROOT / ".github/workflows/test-real-burns-source.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('mv .cuc "$GITHUB_WORKSPACE/../reviewed-cuc"', workflow)
        self.assertNotIn('mv .cuc "$RUNNER_TEMP/reviewed-cuc"', workflow)
        self.assertIn('"$GITHUB_WORKSPACE/../reviewed-cuc/tf/0.2.8"', workflow)

    def test_real_agora_host_precreated_output_acceptance_is_required_in_ci(self):
        workflow = (
            ROOT / ".github/workflows/test-real-burns-source.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("repository: alexsosn/Agora", workflow)
        self.assertIn("0408967b1808c1f22c69e299d302b1e7b5e26354", workflow)
        self.assertIn("bubblewrap", workflow)
        self.assertIn("check_agora_burns_parent_binding.py", workflow)
        verifier = ROOT / "scripts/check_agora_burns_parent_binding.py"
        self.assertTrue(verifier.is_file(), "real Agora host acceptance script missing")
        code = verifier.read_text(encoding="utf-8")
        for marker in (
            "ParentBinding(", "materialize(", "sandbox=\"required\"",
            "burns_headword_1.tf", "otype.tf", "oslots.tf", "otext.tf",
            "source_revision", "maxNode", "maxSlot",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, code)

    def test_manifest_executes_agora_adapter_not_absent_path_cli(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        args = manifest["materializers"][0]["execution"]
        self.assertEqual(args["module"], "ugarit_context_parsing.agora_adapter")
        self.assertEqual(args["args"][0], "{source}")



if __name__ == "__main__":
    unittest.main()
