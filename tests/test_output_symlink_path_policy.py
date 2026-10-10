"""Symlinked publication path regression contracts, both CUC module writers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tf.fabric import Fabric

from test_burns_tf_module import _module_fixture
from test_feature_only_module import _fixture as _feature_fixture
from ugarit_context_parsing.feature_module import write_feature_module
from ugarit_context_parsing.module import write_burns_module


class _NoFabric:
    def __init__(self, **kwargs):
        raise AssertionError("symlink path must be rejected before Fabric")


class _SymlinkRootDuringSave:
    def __init__(self, output: Path, destination: Path):
        self.output = output
        self.destination = destination

    def save(self, **kwargs):
        real = Fabric(locations=[], modules=[], silent="deep")
        ok = real.save(**kwargs)
        self.output.symlink_to(self.destination, target_is_directory=True)
        return ok


class _SwapParentDuringSave:
    def __init__(self, output_parent: Path):
        self.output_parent = output_parent

    def save(self, **kwargs):
        real = Fabric(locations=[], modules=[], silent="deep")
        ok = real.save(**kwargs)
        moved = self.output_parent.with_name(self.output_parent.name + "-moved")
        self.output_parent.rename(moved)
        self.output_parent.symlink_to(moved, target_is_directory=True)
        return ok


class OutputSymlinkPathTests(unittest.TestCase):
    def _alias(self, root: Path) -> tuple[Path, Path]:
        target = root / "real-parent"
        target.mkdir()
        (target / "private-note.txt").write_bytes(b"do not change\n")
        alias = root / "aliased-parent"
        try:
            alias.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("creating directory symlinks is unavailable")
        return target, alias

    def test_feature_only_refuses_symlinked_parent_before_fabric(self):
        _, _, _, module, report = _feature_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            target, alias = self._alias(Path(tmp))
            with self.assertRaisesRegex(ValueError, "symlink"):
                write_feature_module(
                    module, report, alias / "new-feature-module",
                    fabric_factory=_NoFabric,
                )
            self.assertEqual((target / "private-note.txt").read_bytes(), b"do not change\n")
            self.assertFalse((target / "new-feature-module").exists())

    def test_module_v1_refuses_symlinked_parent_before_fabric(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            target, alias = self._alias(Path(tmp))
            with self.assertRaisesRegex(ValueError, "symlink"):
                write_burns_module(
                    module, report, alias / "new-v1-module",
                    fabric_factory=_NoFabric,
                )
            self.assertEqual((target / "private-note.txt").read_bytes(), b"do not change\n")
            self.assertFalse((target / "new-v1-module").exists())

    def test_module_v1_refuses_existing_symlinked_output_root(self):
        _, _, _, module, report = _module_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "owned-module"
            target.mkdir()
            (target / "private-note.txt").write_bytes(b"stay intact\n")
            alias = root / "root-alias"
            try:
                alias.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("creating directory symlinks is unavailable")
            with self.assertRaisesRegex(ValueError, "symlink"):
                write_burns_module(module, report, alias, fabric_factory=_NoFabric)
            self.assertEqual((target / "private-note.txt").read_bytes(), b"stay intact\n")

    def test_both_writers_refuse_dangling_symlink_at_output_root(self):
        _, _, _, old_module, old_report = _module_fixture()
        _, _, _, new_module, new_report = _feature_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            alias = Path(tmp) / "dangling"
            try:
                alias.symlink_to(Path(tmp) / "no-such-directory", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("creating directory symlinks is unavailable")
            for writer, module, report in (
                (write_burns_module, old_module, old_report),
                (write_feature_module, new_module, new_report),
            ):
                with self.subTest(writer=writer.__name__):
                    with self.assertRaisesRegex(ValueError, "symlink"):
                        writer(module, report, alias, fabric_factory=_NoFabric)
                    self.assertTrue(alias.is_symlink())

    def test_symlink_injected_at_output_root_during_save_is_rejected(self):
        _, _, _, old_module, old_report = _module_fixture()
        _, _, _, new_module, new_report = _feature_fixture()
        for writer, module, report in (
            (write_burns_module, old_module, old_report),
            (write_feature_module, new_module, new_report),
        ):
            with self.subTest(writer=writer.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    output = root / "pending-output"
                    target = root / "foreign-target"
                    target.mkdir()
                    (target / "sentinel.txt").write_bytes(b"untouched\n")
                    with self.assertRaisesRegex(ValueError, "symlink"):
                        writer(
                            module, report, output,
                            fabric_factory=lambda **kw: _SymlinkRootDuringSave(
                                output, target
                            ),
                        )
                    self.assertTrue(output.is_symlink())
                    self.assertEqual(
                        sorted(p.name for p in target.iterdir()), ["sentinel.txt"]
                    )
                    self.assertEqual(
                        (target / "sentinel.txt").read_bytes(), b"untouched\n"
                    )

    def test_parent_replaced_by_symlink_during_fabric_save_is_rejected(self):
        _, _, _, old_module, old_report = _module_fixture()
        _, _, _, new_module, new_report = _feature_fixture()
        for writer, module, report in (
            (write_burns_module, old_module, old_report),
            (write_feature_module, new_module, new_report),
        ):
            with self.subTest(writer=writer.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    parent = Path(tmp) / "legitimate-parent"
                    parent.mkdir()
                    output = parent / "module"
                    with self.assertRaisesRegex(ValueError, "symlink"):
                        writer(
                            module, report, output,
                            fabric_factory=lambda **kw: _SwapParentDuringSave(parent),
                        )
                    self.assertTrue(parent.is_symlink())
                    self.assertFalse(output.exists())

    def test_path_with_parent_dotdot_does_not_hide_symlink_alias(self):
        _, _, _, old_module, old_report = _module_fixture()
        _, _, _, new_module, new_report = _feature_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            target, alias = self._alias(Path(tmp))
            output = alias / ".." / "escaped-output"
            for writer, module, report in (
                (write_burns_module, old_module, old_report),
                (write_feature_module, new_module, new_report),
            ):
                with self.subTest(writer=writer.__name__):
                    with self.assertRaisesRegex(ValueError, "symlink"):
                        writer(module, report, output, fabric_factory=_NoFabric)
            self.assertFalse((target.parent / "escaped-output").exists())

    def test_honest_new_parent_is_supported_by_both_writers(self):
        _, _, _, old_module, old_report = _module_fixture()
        _, _, _, new_module, new_report = _feature_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "new-parent-v1" / "module"
            new = root / "new-parent-feature" / "module"
            self.assertTrue(write_burns_module(old_module, old_report, old))
            self.assertTrue(write_feature_module(new_module, new_report, new))
            self.assertTrue((old / "burns-module-report.json").is_file())
            self.assertTrue((new / "burns-feature-module-report.json").is_file())


if __name__ == "__main__":
    unittest.main()
