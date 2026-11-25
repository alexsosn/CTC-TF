"""Acceptance boundary for the pinned, audit-only CUC 0.4.0 candidate (#156)."""
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from ugarit_context_parsing import cuc_index as ci
from ugarit_context_parsing.module import _compatibility_payload


# Independently hashed from the upstream immutable GitHub snapshot.
EXPECTED = {
    "column.tf": (1589, "78a72baa2e80061ff3fc1128acef39df3b1ae4ae427d111a5b35a44094ab0e54"),
    "g_cons.tf": (146536, "ad79f4fcdb2f5161d812fb47dda9f909b067e7e71f8b63d6190e05ebf27f0730"),
    "line.tf": (25080, "b99b306e815058dfef26a072d2c3409d3db3ce7b71306f0d14087451337c68e7"),
    "line_label.tf": (25195, "f96635e705477fdc596ac90bb5f56474a98fd3e16206ecdab24f9fc69b35695c"),
    "oslots.tf": (560299, "c74c54ca500de1a44a7c96dd2af119ad207663ecafc0dc64feab21adc89aef35"),
    "otext.tf": (423, "032cc878bb658713b05e52dba4157d4d001fc818ed89260bf8169c534a4f7c07"),
    "otype.tf": (425, "7287299f8956c59c4c5a2bd8c819ad642db1d2422362108d0876d89d6f66394c"),
    "tablet.tf": (4583, "4e51049020ce21b538caf936b2980bed4c58c8b06195e41754e187655c882f11"),
    "tablet@rih.tf": (4989, "fd2ce6d026f276eee5c23c526889648b39d2d11ff67bd9e0c544ec5bab4777c1"),
}
COMMIT = "64c188da6d2dad0f2960769c40953994900e4571"
MANIFEST = "db7f8cb32a1e7308925994eeeaaa809274b3b0bab0ff0ca33dd7eb89d7ec89aa"
COUNTS = dict(sign=177132, alias=3, boundary=1417, column=534, line=9554, tablet=456, word=33012)


class ProvisionalCucTests(unittest.TestCase):
    def test_pinned_candidate_profile_is_exact(self):
        self.assertEqual(ci.PROVISIONAL_CUC_COMMIT, COMMIT)
        self.assertEqual(ci.PROVISIONAL_CUC_VERSION, "0.4.0")
        self.assertEqual(ci.PROVISIONAL_CUC_COUNTS, COUNTS)
        self.assertIsInstance(ci.PROVISIONAL_CUC_FILES, MappingProxyType)
        self.assertEqual(
            {name: (item.size, item.sha256) for name, item in ci.PROVISIONAL_CUC_FILES.items()},
            EXPECTED,
        )
        self.assertEqual(ci.PROVISIONAL_CUC_SECTION_FEATURES, ("tablet", "column", "line_label"))
        self.assertEqual(ci.PROVISIONAL_CUC_MANIFEST_SHA256, MANIFEST)
        payload = {name: {"size": size, "sha256": digest} for name, (size, digest) in EXPECTED.items()}
        self.assertEqual(hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), MANIFEST)

    def test_provisional_loader_has_no_trust_override(self):
        self.assertEqual(tuple(inspect.signature(ci.build_provisional_cuc_index).parameters), ("path",))
        self.assertEqual(tuple(inspect.signature(ci.build_reviewed_cuc_index).parameters), ("path",))

    def test_provisional_file_gate_checks_every_digest_and_size(self):
        # No upstream corpus bytes are committed. The digest function is mocked
        # ONLY here to isolate the actual path/size/digest/manifest control flow.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, (size, _) in EXPECTED.items():
                (root / name).write_bytes(b"\0" * size)
            with patch.object(ci, "_sha256_file", side_effect=lambda p: EXPECTED[p.name][1]) as digest:
                identity = ci._verify_provisional_cuc_files(root)
                self.assertEqual(identity.commit, COMMIT)
                self.assertEqual(identity.version, "0.4.0")
                self.assertEqual(identity.manifest_sha256, MANIFEST)
                self.assertEqual(set(p.args[0].name for p in digest.call_args_list), set(EXPECTED))
                with self.assertRaisesRegex(ValueError, "compatibility"):
                    _compatibility_payload(SimpleNamespace(compatibility=identity))
            for name, (size, _) in EXPECTED.items():
                with self.subTest(name=name):
                    with patch.object(ci, "_sha256_file", side_effect=lambda p: "0" * 64 if p.name == name else EXPECTED[p.name][1]):
                        with self.assertRaisesRegex(ci.CucCompatibilityError, "fingerprint"):
                            ci._verify_provisional_cuc_files(root)
                    (root / name).write_bytes(b"\0" * (size + 1))
                    with patch.object(ci, "_sha256_file", side_effect=lambda p: EXPECTED[p.name][1]):
                        with self.assertRaisesRegex(ci.CucCompatibilityError, "fingerprint"):
                            ci._verify_provisional_cuc_files(root)
                    (root / name).write_bytes(b"\0" * size)
            # With real hashing, the fabricated files must be refused.
            with self.assertRaisesRegex(ci.CucCompatibilityError, "fingerprint"):
                ci.build_provisional_cuc_index(root)
            with self.assertRaisesRegex(ci.CucCompatibilityError, "fingerprint"):
                ci.build_reviewed_cuc_index(root)

    def test_candidate_requires_otext_and_rejects_symlinked_section_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, (size, _) in EXPECTED.items():
                (root / name).write_bytes(b"\0" * size)
            with patch.object(ci, "_sha256_file", side_effect=lambda p: EXPECTED[p.name][1]):
                (root / "otext.tf").unlink()
                with self.assertRaisesRegex(ci.CucCompatibilityError, "missing"):
                    ci._verify_provisional_cuc_files(root)
                (root / "otext.tf").write_bytes(b"\0" * EXPECTED["otext.tf"][0])
                path = root / "line_label.tf"
                path.rename(root / "actual.tf")
                path.symlink_to(root / "actual.tf")
                with self.assertRaisesRegex(ci.CucCompatibilityError, "symlink"):
                    ci._verify_provisional_cuc_files(root)

    def test_reviewed_identity_unchanged(self):
        self.assertEqual(ci.reviewed_cuc_compatibility_payload()["version"], "0.2.8")
        self.assertEqual(ci.reviewed_cuc_compatibility_payload()["manifest_sha256"], "717e5b7f1c60b800e05f50f4cac27dac7562b45eecb48a8686c64cfab42a92ba")
