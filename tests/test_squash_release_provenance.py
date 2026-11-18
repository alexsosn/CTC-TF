"""Squash merge provenance: exact PR association and immutable reviewed tree."""
import unittest
from scripts.publish_reviewed_release import ReleaseGateError, _reviewed_head_for_merge

MERGE = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40
PARENT = "d" * 40

class FakeAPI:
    def __init__(self):
        self.calls = []
        self.docs = {
            f"commits/{MERGE}": {"sha": MERGE, "commit": {"tree": {"sha": TREE}}, "parents": [{"sha": PARENT}]},
            f"commits/{HEAD}": {"sha": HEAD, "commit": {"tree": {"sha": TREE}}, "parents": [{"sha": PARENT}]},
            f"commits/{MERGE}/pulls": [{
                "number": 147, "state": "closed", "merged_at": "2026-11-18T17:00:20Z",
                "merge_commit_sha": MERGE, "head": {"sha": HEAD},
                "base": {"ref": "master", "repo": {"full_name": "alexsosn/CTC-TF"}},
            }],
        }
    def request(self, method, path, payload=None, *, allow_missing=False):
        self.calls.append((method, path))
        if method != "GET":
            raise AssertionError("provenance verification must be read-only")
        return self.docs[path]

class SquashReleaseProvenanceTests(unittest.TestCase):
    def test_real_shape_squash_merge_resolves_reviewed_head(self):
        api = FakeAPI()
        self.assertEqual(_reviewed_head_for_merge(api, MERGE), HEAD)
        self.assertTrue(all(method == "GET" for method, _ in api.calls))

    def test_forged_pr_associations_fail_closed(self):
        for field, value in (
            ("merge_commit_sha", PARENT), ("merged_at", None),
            ("state", "open"),
        ):
            with self.subTest(field=field):
                api = FakeAPI()
                api.docs[f"commits/{MERGE}/pulls"][0][field] = value
                with self.assertRaises(ReleaseGateError):
                    _reviewed_head_for_merge(api, MERGE)
        for field, value in (("ref", "other"), ("repo", {"full_name": "other/repo"})):
            with self.subTest(field=field):
                api = FakeAPI()
                api.docs[f"commits/{MERGE}/pulls"][0]["base"][field] = value
                with self.assertRaises(ReleaseGateError):
                    _reviewed_head_for_merge(api, MERGE)

    def test_mismatched_tree_or_missing_pr_fail_closed(self):
        api = FakeAPI()
        api.docs[f"commits/{HEAD}"]["commit"]["tree"]["sha"] = "e" * 40
        with self.assertRaisesRegex(ReleaseGateError, "tree"):
            _reviewed_head_for_merge(api, MERGE)
        api = FakeAPI()
        api.docs[f"commits/{MERGE}/pulls"] = []
        with self.assertRaises(ReleaseGateError):
            _reviewed_head_for_merge(api, MERGE)

    def test_ambiguous_pr_association_fails_closed(self):
        api = FakeAPI()
        api.docs[f"commits/{MERGE}/pulls"].append(dict(api.docs[f"commits/{MERGE}/pulls"][0], number=148))
        with self.assertRaises(ReleaseGateError):
            _reviewed_head_for_merge(api, MERGE)

    def test_non_squash_commit_is_not_accepted_as_squash(self):
        api = FakeAPI()
        api.docs[f"commits/{MERGE}"]["parents"].append({"sha": HEAD})
        with self.assertRaises(ReleaseGateError):
            _reviewed_head_for_merge(api, MERGE)

if __name__ == "__main__":
    unittest.main()
