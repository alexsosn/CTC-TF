"""Adversarial publication tests: an empty destination must not be replaced.

An existence check followed by Path.replace has a TOCTOU window: POSIX can
replace a newly created *empty* directory. The final rename must itself
refuse a destination, independent of prior checks.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ugarit_context_parsing.entity_writer import _publish_stage_noreplace


class AtomicExclusivePublishTests(unittest.TestCase):
    def test_empty_foreign_directory_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "stage"
            stage.mkdir()
            (stage / "ready.tf").write_text("ours", encoding="utf-8")
            foreign = root / "foreign"
            foreign.mkdir()
            with self.assertRaises(FileExistsError):
                _publish_stage_noreplace(stage, foreign)
            self.assertTrue(foreign.is_dir())
            self.assertEqual(tuple(foreign.iterdir()), ())
            self.assertEqual((stage / "ready.tf").read_text(encoding="utf-8"), "ours")

    def test_foreign_file_and_symlink_are_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for kind in ("file", "symlink"):
                with self.subTest(kind=kind):
                    stage = root / f"stage-{kind}"
                    stage.mkdir()
                    (stage / "ready.tf").write_text("ours", encoding="utf-8")
                    dest = root / f"foreign-{kind}"
                    if kind == "file":
                        dest.write_text("foreign", encoding="utf-8")
                    else:
                        dest.symlink_to(root / "absent")
                    with self.assertRaises(FileExistsError):
                        _publish_stage_noreplace(stage, dest)
                    self.assertTrue(stage.is_dir())
                    if kind == "file":
                        self.assertEqual(dest.read_text(encoding="utf-8"), "foreign")
                    else:
                        self.assertTrue(dest.is_symlink())
                        self.assertEqual(dest.readlink(), root / "absent")

    def test_fresh_destination_gets_complete_stage_by_one_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "stage"
            stage.mkdir()
            (stage / "ready.tf").write_text("ours", encoding="utf-8")
            dest = root / "fresh"
            _publish_stage_noreplace(stage, dest)
            self.assertFalse(stage.exists())
            self.assertEqual((dest / "ready.tf").read_text(encoding="utf-8"), "ours")


if __name__ == "__main__":
    unittest.main()
