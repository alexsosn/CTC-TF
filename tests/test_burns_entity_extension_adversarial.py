"""Independent consumer-view tests: caller-provided CUC warp must match index."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tf.fabric import Fabric

from test_burns_tf_module import _index, _source
from test_burns_entity_extension import _write_indexed_base
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.entity_extension import build_entity_extension


class EntityExtensionWarpMismatchTests(unittest.TestCase):
    def test_different_word_transliteration_on_same_node_fails_closed(self):
        source, index = _source(), _index()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "cuc"
            _write_indexed_base(base)
            api = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            forged_g_cons = SimpleNamespace(
                v=lambda node: "WRONG" if node == 8 else api.F.g_cons.v(node)
            )
            forged = SimpleNamespace(
                F=SimpleNamespace(otype=api.F.otype, g_cons=forged_g_cons), E=api.E,
            )
            with self.assertRaisesRegex(ValueError, "CUC.*index|warp.*mismatch"):
                build_entity_extension(source, align_burns_source(source, index), index, forged)

    def test_node_count_mismatch_is_rejected_before_projection(self):
        source, index = _source(), _index()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "cuc"
            _write_indexed_base(base)
            api = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            forged_otype = SimpleNamespace(
                maxNode=api.F.otype.maxNode + 1,
                maxSlot=api.F.otype.maxSlot,
                v=api.F.otype.v,
            )
            forged = SimpleNamespace(
                F=SimpleNamespace(otype=forged_otype, g_cons=api.F.g_cons), E=api.E,
            )
            with self.assertRaisesRegex(ValueError, "CUC.*index|warp.*mismatch"):
                build_entity_extension(source, align_burns_source(source, index), index, forged)

    def test_word_sign_extent_mismatch_is_rejected_before_projection(self):
        """Equal counts/types/transcriptions must not hide a different word warp."""
        source, index = _source(), _index()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "cuc"
            _write_indexed_base(base)
            api = Fabric(locations=[str(base)], modules=[""], silent="deep").loadAll(silent="deep")
            real_oslots = api.E.oslots
            forged_oslots = SimpleNamespace(
                s=lambda node: (1,) if node == 8 else real_oslots.s(node)
            )
            forged = SimpleNamespace(
                F=SimpleNamespace(otype=api.F.otype, g_cons=api.F.g_cons),
                E=SimpleNamespace(oslots=forged_oslots),
            )
            with self.assertRaisesRegex(ValueError, "CUC.*index|warp.*mismatch"):
                build_entity_extension(
                    source,
                    align_burns_source(source, index),
                    index,
                    forged,
                )


if __name__ == "__main__":
    unittest.main()
