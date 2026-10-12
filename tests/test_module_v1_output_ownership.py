"""Source-safe output ownership contracts for explicit legacy CUC module-v1."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_tf_module import _module_fixture, EXPECTED_FILES, REPORT_FILE
from ugarit_context_parsing.module import write_burns_module


class _MustNotConstruct:
    def __init__(self, **kwargs):
        raise AssertionError("ownership validation happened after Fabric construction")


class _InjectDuringSave:
    def __init__(self, output: Path):
        self.output = output

    def save(self, **kwargs):
        real = Fabric(locations=[], modules=[], silent="deep")
        ok = real.save(**kwargs)
        (self.output / "burns_custom.tf").write_bytes(b"foreign-added-during-save\n")
        return ok


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in root.iterdir() if path.is_file()
    }


class ModuleV1OwnershipTests(unittest.TestCase):
    def test_unknown_prefixed_file_is_rejected_before_fabric_and_untouched(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            output.mkdir()
            foreign = output / "burns_custom.tf"
            foreign.write_bytes(b"private-foreign-data\n")
            before = _snapshot(output)
            with self.assertRaisesRegex(ValueError, "unknown|unexpected|ownership"):
                write_burns_module(
                    module, report, output, fabric_factory=_MustNotConstruct
                )
            self.assertEqual(_snapshot(output), before)

    def test_valid_complete_previous_module_is_replaceable_preserving_notes(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            self.assertTrue(write_burns_module(module, report, output))
            (output / "private-notes.txt").write_bytes(b"keep me\n")
            self.assertTrue(write_burns_module(module, report, output))
            self.assertEqual((output / "private-notes.txt").read_bytes(), b"keep me\n")
            self.assertEqual(
                {p.name for p in output.iterdir() if p.suffix == ".tf"},
                EXPECTED_FILES,
            )
            self.assertEqual(
                json.loads((output / REPORT_FILE).read_text())["feature_inventory"],
                sorted(x[:-3] for x in EXPECTED_FILES),
            )

    def test_incomplete_existing_module_fails_before_fabric_unchanged(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            self.assertTrue(write_burns_module(module, report, output))
            (output / "burns_headwords.tf").unlink()
            before = _snapshot(output)
            with self.assertRaisesRegex(ValueError, "incomplete|inventory|ownership"):
                write_burns_module(
                    module, report, output, fabric_factory=_MustNotConstruct
                )
            self.assertEqual(_snapshot(output), before)

    def test_forged_or_invalid_existing_report_fails_before_fabric(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            self.assertTrue(write_burns_module(module, report, output))
            old = json.loads((output / REPORT_FILE).read_text())
            for change in ("missing", "wrong_schema", "wrong_inventory", "wrong_cuc"):
                with self.subTest(change=change):
                    (output / REPORT_FILE).write_text(
                        json.dumps(old) + "\n", encoding="utf-8"
                    )
                    if change == "missing":
                        (output / REPORT_FILE).unlink()
                    else:
                        forged = dict(old)
                        if change == "wrong_schema":
                            forged["schema"] = "foreign"
                        elif change == "wrong_inventory":
                            forged["feature_inventory"] = ["burns_annotations"]
                        else:
                            forged["cuc_compatibility"] = {"commit": "foreign"}
                        (output / REPORT_FILE).write_text(
                            json.dumps(forged) + "\n", encoding="utf-8"
                        )
                    before = _snapshot(output)
                    with self.assertRaisesRegex(ValueError, "report|ownership"):
                        write_burns_module(
                            module, report, output,
                            fabric_factory=_MustNotConstruct,
                        )
                    self.assertEqual(_snapshot(output), before)

    def test_unknown_prefixed_file_injected_during_stage_cannot_be_deleted(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "module"
            self.assertTrue(write_burns_module(module, report, output))
            prior = _snapshot(output)
            with self.assertRaisesRegex(ValueError, "unknown|unexpected|ownership"):
                write_burns_module(
                    module, report, output,
                    fabric_factory=lambda **kw: _InjectDuringSave(output),
                )
            self.assertEqual(
                (output / "burns_custom.tf").read_bytes(),
                b"foreign-added-during-save\n",
            )
            for name, data in prior.items():
                self.assertEqual((output / name).read_bytes(), data)


    def test_staged_expected_feature_symlink_is_rejected_without_publication(self):
        """Expected feature filenames must not launder links to foreign data."""
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "existing-module"
            self.assertTrue(write_burns_module(module, report, output))
            before = _snapshot(output)
            foreign = root / "private-source.tf"
            foreign.write_bytes(b"PRIVATE-SENTINEL\\n")

            class _SymlinkFeatureFabric:
                def save(self, **kwargs):
                    stage = Path(kwargs["location"])
                    stage.mkdir(parents=True, exist_ok=True)
                    for name in EXPECTED_FILES:
                        file = stage / name
                        if name == "burns_headwords.tf":
                            file.symlink_to(foreign)
                        else:
                            file.write_bytes(b"synthetic-stage-feature\\n")
                    return True

            with self.assertRaisesRegex(RuntimeError, "symlink|non-regular"):
                write_burns_module(
                    module, report, output,
                    fabric_factory=lambda **kwargs: _SymlinkFeatureFabric(),
                )
            self.assertEqual(_snapshot(output), before)
            self.assertEqual(foreign.read_bytes(), b"PRIVATE-SENTINEL\\n")
            self.assertFalse(any(path.is_symlink() for path in output.iterdir()))


    def test_staged_report_symlink_must_not_overwrite_foreign_file(self):
        """A staged report link must be refused before write_text follows it."""
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "existing-module"
            self.assertTrue(write_burns_module(module, report, output))
            before = _snapshot(output)
            foreign = root / "private-report"
            original = b"PRIVATE-REPORT-SENTINEL\\n"
            foreign.write_bytes(original)

            class _SymlinkReportFabric:
                def save(self, **kwargs):
                    stage = Path(kwargs["location"])
                    stage.mkdir(parents=True, exist_ok=True)
                    for name in EXPECTED_FILES:
                        (stage / name).write_bytes(b"synthetic-stage-feature\\n")
                    (stage / REPORT_FILE).symlink_to(foreign)
                    return True

            with self.assertRaisesRegex(RuntimeError, "report|symlink|non-regular"):
                write_burns_module(
                    module, report, output,
                    fabric_factory=lambda **kwargs: _SymlinkReportFabric(),
                )
            self.assertEqual(foreign.read_bytes(), original)
            self.assertEqual(_snapshot(output), before)
            self.assertFalse(any(path.is_symlink() for path in output.iterdir()))


if __name__ == "__main__":
    unittest.main()
