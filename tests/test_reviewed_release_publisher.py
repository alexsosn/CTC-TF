"""Fake API regression tests for the manual reviewed v0.3.0 publisher."""
from __future__ import annotations
import base64
import copy
import json
import unittest
from pathlib import Path

from scripts.publish_reviewed_release import (
    EXPECTED_PR_WORKFLOWS, REPOSITORY, ReleaseGateError, publish_reviewed_release,
)

MERGE = "a" * 40
PR_HEAD = "b" * 40
TREE = "c" * 40


def encoded(content):
    return {"encoding": "base64",
            "content": base64.b64encode(content.encode()).decode()}


class FakeGitHub:
    def __init__(self):
        self.calls = []
        self.paths = {
            "git/ref/heads/master": {
                "ref": "refs/heads/master", "object": {"type": "commit", "sha": MERGE}},
            f"commits/{MERGE}": {
                "sha": MERGE, "commit": {"tree": {"sha": TREE}},
                "parents": [{"sha": "d" * 40}, {"sha": PR_HEAD}]},
            f"commits/{PR_HEAD}": {
                "sha": PR_HEAD, "commit": {"tree": {"sha": TREE}}},
            f"actions/runs?head_sha={PR_HEAD}&per_page=100": {
                "workflow_runs": [self.run(name, PR_HEAD, "pull_request", i)
                                  for i, name in enumerate(sorted(EXPECTED_PR_WORKFLOWS), 1)]},
            f"actions/runs?head_sha={MERGE}&per_page=100": {
                "workflow_runs": [self.run("Tests", MERGE, "push", 20)]},
            f"contents/pyproject.toml?ref={MERGE}": encoded(
                '[project]\nname = "ugarit-context-parsing"\nversion = "0.3.0"\n'),
            f"contents/agora.materializer.json?ref={MERGE}": encoded(json.dumps({
                "plugin": {"id": "cuc-burns", "version": "0.3.0"},
                "materializers": [{
                    "id": "cuc-burns-csv",
                    "acquisition": [{"type": "user-local"}],
                    "input": {"allow_symlinks": False},
                    "parent_input": {"resource": "cuc", "parent_versions": ["0.2.8"]},
                    "execution": {"module": "ugarit_context_parsing.agora_adapter",
                                  "network": "deny", "args": ["{source}", "{parent}"]},
                    "output": {"composition": {"kind": "feature-module", "parent": "cuc"}},
                }],
            })),
            f"contents/docs/releases/v0.3.0.md?ref={MERGE}": encoded(
                "# Ugarit Context Parsing v0.3.0\n"
                "feature-only Burns module with agora.materializer.json.\n"
                "No Burns-derived data files are attached to the release.\n"),
        }

    @staticmethod
    def run(name, sha, event, number):
        return {"id": number, "name": name, "head_sha": sha,
                "event": event, "status": "completed", "conclusion": "success",
                "run_number": number, "run_attempt": 1,
                "created_at": f"2026-10-11T{number % 24:02d}:00:00Z"}

    def request(self, method, path, payload=None, *, allow_missing=False):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if method == "GET":
            if path not in self.paths and not allow_missing:
                raise AssertionError(f"unmocked API read: {path}")
            return copy.deepcopy(self.paths.get(path))
        if method == "POST" and path == "git/refs":
            assert payload["ref"] == "refs/tags/v0.3.0"
            self.paths["git/ref/tags/v0.3.0"] = {
                "ref": payload["ref"], "object": {"type": "commit", "sha": payload["sha"]}}
            return self.paths["git/ref/tags/v0.3.0"]
        if method == "POST" and path == "releases":
            self.paths["releases/tags/v0.3.0"] = {
                "tag_name": payload["tag_name"], "name": payload["name"],
                "body": payload["body"], "draft": payload["draft"],
                "prerelease": payload["prerelease"], "assets": []}
            return self.paths["releases/tags/v0.3.0"]
        raise AssertionError(f"unexpected API write: {method} {path}")


def call(api, *, publish=False, sha=MERGE, confirm=None,
         git_ref="refs/heads/master", git_sha=MERGE):
    return publish_reviewed_release(
        api, repository=REPOSITORY, expected_sha=sha,
        confirmation=confirm if confirm is not None else f"v0.3.0@{sha}",
        github_ref=git_ref, github_sha=git_sha, publish=publish,
    )


class ReviewedReleasePublisherTests(unittest.TestCase):
    def test_preflight_is_read_only(self):
        api = FakeGitHub()
        self.assertFalse(call(api)["published"])
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_publishes_exact_tag_with_no_assets(self):
        api = FakeGitHub()
        answer = call(api, publish=True)
        self.assertTrue(answer["published"])
        self.assertEqual(answer["commit"], MERGE)
        self.assertEqual(api.paths["git/ref/tags/v0.3.0"]["object"]["sha"], MERGE)
        self.assertEqual(api.paths["releases/tags/v0.3.0"]["assets"], [])
        writes = [(method, path) for method, path, _ in api.calls if method == "POST"]
        self.assertEqual(writes, [("POST", "git/refs"), ("POST", "releases")])

    def test_wrong_confirmation_ref_sha_or_moving_master_fail_before_writes(self):
        for variant in ("wrong_confirmation", "wrong_ref", "wrong_sha", "moving_master"):
            with self.subTest(variant=variant):
                api = FakeGitHub()
                opts = {}
                if variant == "wrong_confirmation":
                    opts["confirm"] = "wrong"
                elif variant == "wrong_ref":
                    opts["git_ref"] = "refs/heads/unreviewed"
                elif variant == "wrong_sha":
                    opts["git_sha"] = "e" * 40
                else:
                    api.paths["git/ref/heads/master"]["object"]["sha"] = "f" * 40
                with self.assertRaises(ReleaseGateError):
                    call(api, publish=True, **opts)
                self.assertFalse(any(m == "POST" for m, _, _ in api.calls))

    def test_different_reviewed_tree_is_rejected(self):
        api = FakeGitHub()
        api.paths[f"commits/{PR_HEAD}"]["commit"]["tree"]["sha"] = "e" * 40
        with self.assertRaisesRegex(ReleaseGateError, "tree"):
            call(api, publish=True)

    def test_failed_missing_or_stale_pr_workflow_blocks_release(self):
        key = f"actions/runs?head_sha={PR_HEAD}&per_page=100"
        for variant in ("missing", "failed", "newer_failure"):
            with self.subTest(variant=variant):
                api = FakeGitHub()
                runs = api.paths[key]["workflow_runs"]
                if variant == "missing":
                    runs.pop()
                elif variant == "failed":
                    runs[0]["conclusion"] = "failure"
                else:
                    runs.append(dict(runs[0], id=1000, run_number=1000,
                                     created_at="2026-10-12T00:00:00Z",
                                     conclusion="failure"))
                with self.assertRaisesRegex(ReleaseGateError, "workflow"):
                    call(api, publish=True)
                self.assertFalse(any(m == "POST" for m, _, _ in api.calls))

    def test_missing_merge_push_ci_blocks_release(self):
        api = FakeGitHub()
        api.paths[f"actions/runs?head_sha={MERGE}&per_page=100"]["workflow_runs"] = []
        with self.assertRaisesRegex(ReleaseGateError, "workflow"):
            call(api, publish=True)

    def test_bad_package_manifest_or_notes_rejected(self):
        for path, content in (
            (f"contents/pyproject.toml?ref={MERGE}",
             '[project]\nversion = "0.4.0"\n'),
            (f"contents/agora.materializer.json?ref={MERGE}",
             '{"plugin":{"version":"0.4.0"},"materializers":[]}'),
            (f"contents/docs/releases/v0.3.0.md?ref={MERGE}",
             "feature-only without the required source restriction"),
        ):
            with self.subTest(path=path):
                api = FakeGitHub()
                api.paths[path] = encoded(content)
                with self.assertRaises(ReleaseGateError):
                    call(api, publish=True)

    def test_existing_wrong_tag_or_release_blocks_publication(self):
        for variant in ("wrong_tag", "existing_release"):
            with self.subTest(variant=variant):
                api = FakeGitHub()
                api.paths["git/ref/tags/v0.3.0"] = {
                    "ref": "refs/tags/v0.3.0",
                    "object": {"type": "commit",
                               "sha": "f" * 40 if variant == "wrong_tag" else MERGE}}
                if variant == "existing_release":
                    api.paths["releases/tags/v0.3.0"] = {"tag_name": "v0.3.0", "assets": []}
                with self.assertRaises(ReleaseGateError):
                    call(api, publish=True)
                self.assertFalse(any(m == "POST" for m, _, _ in api.calls))

    def test_matching_tag_recovers_interrupted_publication(self):
        api = FakeGitHub()
        api.paths["git/ref/tags/v0.3.0"] = {
            "ref": "refs/tags/v0.3.0",
            "object": {"type": "commit", "sha": MERGE}}
        self.assertTrue(call(api, publish=True)["published"])
        self.assertEqual([(m, p) for m, p, _ in api.calls if m == "POST"],
                         [("POST", "releases")])

    def test_manual_workflow_is_write_scoped_and_no_automatic_publish(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/publish-reviewed-v0.3.0.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        for forbidden in ("  push:", "  pull_request:", "  schedule:", "upload-artifact"):
            self.assertNotIn(forbidden, workflow)
        for required in ("contents: write", "refs/heads/master",
                         "release_confirmation", "--publish", "GH_TOKEN:",
                         "persist-credentials: false"):
            self.assertIn(required, workflow)


if __name__ == "__main__":
    unittest.main()
