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


if __name__ == "__main__":
    unittest.main()
