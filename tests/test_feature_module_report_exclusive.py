"""Source-safe primary Burns feature-module report no-follow regression.

A private staged report symlink inserted *after* inventory snapshot must not
cause the publication writer to overwrite foreign local data.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tf.fabric import Fabric

from test_feature_only_module import _fixture
from ugarit_context_parsing.feature_module import REPORT_FILE, write_feature_module


class PrimaryFeatureModuleReportTests(unittest.TestCase):
    def test_staged_report_link_injected_after_inventory_snapshot_is_rejected(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "new-feature-only-module"
            foreign = root / "private-foreign-data"
            sentinel = b"foreign-sentinel-before-publication\n"
            foreign.write_bytes(sentinel)
            installed_patches = []
            injections = []

            class _RaceAfterSaveFabric:
                def __init__(self, **kwargs):
                    self.fabric = Fabric(**kwargs)

                def save(self, **kwargs):
                    saved = self.fabric.save(**kwargs)
                    if not saved:
                        return False
                    stage = Path(kwargs["location"])
                    real_iterdir = Path.iterdir

                    def inject_after_inventory_snapshot(path):
                        if path == stage and not injections:
                            snapshot = tuple(real_iterdir(path))
                            # The actual inventory sees the old snapshot, while
                            # the next report write sees a new path.
                            (stage / REPORT_FILE).symlink_to(foreign)
                            injections.append(stage)
                            return iter(snapshot)
                        return real_iterdir(path)

                    active = patch.object(Path, "iterdir", inject_after_inventory_snapshot)
                    active.start()
                    installed_patches.append(active)
                    return True

            try:
                with self.assertRaisesRegex(RuntimeError, "report|symlink|exists"):
                    write_feature_module(
                        module, report, output, fabric_factory=_RaceAfterSaveFabric,
                    )
            finally:
                for active in reversed(installed_patches):
                    active.stop()

            self.assertEqual(len(injections), 1, "race injection was not exercised")
            self.assertEqual(foreign.read_bytes(), sentinel)
            self.assertFalse(output.exists(), "refused publication must not create output")

    def test_context_fabric_gate_watches_primary_feature_writer(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/test-context-fabric-burns-module.yml"
        ).read_text(encoding="utf-8")
        pr_filters = workflow.split("pull_request:", 1)[1].split("permissions:", 1)[0]
        self.assertIn(
            "'src/ugarit_context_parsing/feature_module.py'",
            pr_filters,
            "writer changes must trigger the downstream Context-Fabric contract",
        )

    def test_normal_report_still_publishes_as_regular_file(self):
        _, _, _, module, report = _fixture()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "module"
            self.assertTrue(write_feature_module(module, report, output))
            self.assertTrue((output / REPORT_FILE).is_file())
            self.assertFalse((output / REPORT_FILE).is_symlink())
            self.assertFalse(
                {"otype.tf", "oslots.tf", "otext.tf"} &
                {p.name for p in output.iterdir()}
            )


if __name__ == "__main__":
    unittest.main()
