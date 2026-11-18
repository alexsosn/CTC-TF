"""V0.3.1 release gate regression using a reviewed squash-merge GitHub fixture."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.publish_reviewed_release import (
    REPOSITORY, ReleaseGateError, publish_reviewed_release,
)
from test_reviewed_release_publisher import (
    FakeGitHub, MERGE, PR_HEAD, TREE, encoded,
)


class FakeRelease031(FakeGitHub):
    def __init__(self):
        super().__init__()
        self.paths[f"commits/{MERGE}"]["parents"] = [{"sha": "d" * 40}]
        self.paths[f"commits/{MERGE}/pulls"] = [{
            "number": 152, "state": "closed",
            "merged_at": "2026-11-18T20:00:00Z",
            "merge_commit_sha": MERGE,
            "head": {"sha": PR_HEAD},
            "base": {"ref": "master", "repo": {"full_name": REPOSITORY}},
        }]
        self.paths[f"contents/pyproject.toml?ref={MERGE}"] = encoded(
            '[project]\nname = "ugarit-context-parsing"\nversion = "0.3.1"\n'
        )
        manifest = json.loads(__import__("base64").b64decode(
            self.paths[f"contents/agora.materializer.json?ref={MERGE}"]["content"]
        ))
        manifest["plugin"]["version"] = "0.3.1"
        self.paths[f"contents/agora.materializer.json?ref={MERGE}"] = encoded(
            json.dumps(manifest)
        )
        self.paths[f"contents/docs/releases/v0.3.1.md?ref={MERGE}"] = encoded(
            "# Ugarit Context Parsing v0.3.1\n"
            "feature-only CUC module and all-lanes researcher query.\n"
            "Uses agora.materializer.json.\n"
            "No Burns-derived data files are attached to the release.\n"
        )
        self.paths[
            f"contents/src/ugarit_context_parsing/research_queries.py?ref={MERGE}"
        ] = encoded("def iter_burns_occurrences(api):\n    pass\n")

    def request(self, method, path, payload=None, *, allow_missing=False):
        if method == "POST" and path == "git/refs":
            self.calls.append((method, path, payload))
            assert payload["ref"] == "refs/tags/v0.3.1"
            self.paths["git/ref/tags/v0.3.1"] = {
                "ref": payload["ref"], "object": {"type": "commit", "sha": payload["sha"]}
            }
            return self.paths["git/ref/tags/v0.3.1"]
        if method == "POST" and path == "releases":
            self.calls.append((method, path, payload))
            assert payload["tag_name"] == "v0.3.1"
            self.paths["releases/tags/v0.3.1"] = {
                "tag_name": payload["tag_name"],
                "body": payload["body"],
                "draft": payload["draft"], "prerelease": payload["prerelease"],
                "assets": [],
            }
            return self.paths["releases/tags/v0.3.1"]
        return super().request(method, path, payload, allow_missing=allow_missing)


def call(api, *, publish=False, confirm=None):
    return publish_reviewed_release(
        api, repository=REPOSITORY, expected_sha=MERGE,
        confirmation=confirm if confirm is not None else f"v0.3.1@{MERGE}",
        github_ref="refs/heads/master", github_sha=MERGE,
        version="0.3.1", publish=publish,
    )


class ReviewedRelease031Tests(unittest.TestCase):
    def test_new_version_preflight_is_read_only(self):
        api = FakeRelease031()
        result = call(api)
        self.assertEqual(result["tag"], "v0.3.1")
        self.assertEqual(result["reviewed_head"], PR_HEAD)
        self.assertFalse(result["published"])
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_new_version_publishes_only_its_tag_and_restricted_data_free_release(self):
        api = FakeRelease031()
        result = call(api, publish=True)
        self.assertTrue(result["published"])
        self.assertEqual(api.paths["git/ref/tags/v0.3.1"]["object"]["sha"], MERGE)
        self.assertEqual(api.paths["releases/tags/v0.3.1"]["assets"], [])
        self.assertNotIn("git/ref/tags/v0.3.0", api.paths)
        self.assertEqual(
            [path for method, path, _ in api.calls if method == "POST"],
            ["git/refs", "releases"],
        )

    def test_unreviewed_squash_or_mismatched_tree_never_publishes(self):
        for case in ("missing_pr", "wrong_pr_commit", "wrong_tree", "wrong_target"):
            with self.subTest(case=case):
                api = FakeRelease031()
                prs = api.paths[f"commits/{MERGE}/pulls"]
                if case == "missing_pr":
                    prs.clear()
                elif case == "wrong_pr_commit":
                    prs[0]["merge_commit_sha"] = "e" * 40
                elif case == "wrong_tree":
                    api.paths[f"commits/{PR_HEAD}"]["commit"]["tree"]["sha"] = "f" * 40
                elif case == "wrong_target":
                    prs[0]["base"]["repo"]["full_name"] = "other/fork"
                with self.assertRaises(ReleaseGateError):
                    call(api, publish=True)
                self.assertFalse(any(m == "POST" for m, _, _ in api.calls))

    def test_fail_closed_for_missing_ci_moving_master_and_version_mismatch(self):
        for case in ("failed_pr_ci", "missing_push_ci", "moving_master",
                     "wrong_version", "wrong_confirmation"):
            with self.subTest(case=case):
                api = FakeRelease031()
                if case == "failed_pr_ci":
                    runs = api.paths[f"actions/runs?head_sha={PR_HEAD}&per_page=100"]
                    runs["workflow_runs"][0]["conclusion"] = "failure"
                elif case == "missing_push_ci":
                    api.paths[f"actions/runs?head_sha={MERGE}&per_page=100"]["workflow_runs"] = []
                elif case == "moving_master":
                    api.paths["git/ref/heads/master"]["object"]["sha"] = "e" * 40
                elif case == "wrong_version":
                    api.paths[f"contents/pyproject.toml?ref={MERGE}"] = encoded(
                        '[project]\nversion = "0.3.0"\n'
                    )
                with self.assertRaises(ReleaseGateError):
                    call(api, publish=True, confirm="wrong" if case == "wrong_confirmation" else None)
                self.assertFalse(any(m == "POST" for m, _, _ in api.calls))

    def test_existing_release_blocks_duplicate_publication(self):
        api = FakeRelease031()
        api.paths["releases/tags/v0.3.1"] = {"tag_name": "v0.3.1", "assets": []}
        with self.assertRaises(ReleaseGateError):
            call(api, publish=True)
        self.assertFalse(any(m == "POST" for m, _, _ in api.calls))

    def test_v031_manual_workflow_is_dispatch_only(self):
        workflow = (Path(__file__).resolve().parents[1]
                    / ".github/workflows/publish-reviewed-v0.3.1.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("scripts/publish_reviewed_v031.py --publish", workflow)
        self.assertIn("refs/heads/master", workflow)
        self.assertIn("persist-credentials: false", workflow)
        for forbidden in ("  push:", "  pull_request:", "  schedule:", "upload-artifact"):
            self.assertNotIn(forbidden, workflow)

if __name__ == "__main__":
    unittest.main()
