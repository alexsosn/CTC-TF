"""Fail-closed, explicit publication of the reviewed v0.3.0 GitHub Release.

Default mode only checks immutable release evidence; --publish is manual-only.
All release notes and version evidence come from the exact selected Git commit.
No licensed Burns input data or corpus artifacts are acquired or uploaded.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from typing import Any


REPOSITORY = "alexsosn/CTC-TF"
VERSION = "0.3.0"
TAG = f"v{VERSION}"
EXPECTED_PR_WORKFLOWS = frozenset({
    "Tests",
    "Reviewed CUC index contract",
    "Reviewed CUC Burns feature-only module",
    "Context-Fabric Burns module contract",
    "Real Burns Workbooks feature-only acceptance",
    "Appendix CUC concordance audit",
})
_SHA = re.compile(r"[0-9a-f]{40}\Z")


class ReleaseGateError(RuntimeError):
    """A release precondition or publication assertion failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseGateError(message)


class GitHubCLI:
    """Authenticated GitHub REST bridge; all mutating calls remain explicit."""

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None,
        *, allow_missing: bool = False,
    ) -> dict[str, Any] | None:
        _require(method in {"GET", "POST"}, "unsupported GitHub HTTP method")
        cmd = ["gh", "api", f"repos/{REPOSITORY}/{path}"]
        data = None
        if method == "POST":
            _require(isinstance(payload, dict), "POST payload is required")
            cmd += ["-X", "POST", "--input", "-"]
            data = json.dumps(payload, ensure_ascii=False)
        proc = subprocess.run(
            cmd, input=data, text=True, capture_output=True, check=False,
        )
        if proc.returncode != 0:
            if method == "GET" and allow_missing and "HTTP 404" in proc.stderr:
                return None
            raise ReleaseGateError(
                f"GitHub API {method} {path} rejected the request "
                f"(exit {proc.returncode}); nothing is assumed published"
            )
        try:
            doc = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ReleaseGateError(
                f"GitHub API {method} {path} returned non-JSON data"
            ) from exc
        _require(isinstance(doc, dict), "GitHub API returned non-object JSON")
        return doc


def _get(api: Any, path: str, *, allow_missing: bool = False) -> dict | None:
    return api.request("GET", path, allow_missing=allow_missing)


def _contents(api: Any, path: str, sha: str) -> str:
    doc = _get(api, f"contents/{path}?ref={sha}")
    _require(isinstance(doc, dict) and doc.get("encoding") == "base64",
             f"reviewed file {path} must be a base64 GitHub Contents response")
    try:
        encoded = doc["content"].replace("\n", "")
        return base64.b64decode(encoded, validate=True).decode("utf-8")
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise ReleaseGateError(f"invalid immutable file contents for {path}") from exc


def _tree(api: Any, sha: str) -> tuple[str, list[str]]:
    doc = _get(api, f"commits/{sha}")
    try:
        tree = doc["commit"]["tree"]["sha"]
        parents = [parent["sha"] for parent in doc.get("parents", [])]
    except (TypeError, KeyError) as exc:
        raise ReleaseGateError(f"GitHub commit {sha} lacks tree or parents") from exc
    _require(doc.get("sha") == sha and isinstance(tree, str) and _SHA.fullmatch(tree),
             f"GitHub commit {sha} tree identity is invalid")
    return tree, parents


def _latest_successful_workflows(
    api: Any, sha: str, *, event: str, required: frozenset[str],
) -> None:
    doc = _get(api, f"actions/runs?head_sha={sha}&per_page=100")
    _require(isinstance(doc, dict) and isinstance(doc.get("workflow_runs"), list),
             f"missing workflow evidence for {sha}")
    runs = doc["workflow_runs"]
    for name in sorted(required):
        matching = [
            run for run in runs
            if isinstance(run, dict)
            and run.get("name") == name
            and run.get("event") == event
            and run.get("head_sha") == sha
        ]
        _require(matching, f"missing exact-head {event} workflow: {name}")
        # GitHub returns current attempts; a stale successful earlier run must
        # not override a newer failure on the same commit and workflow name.
        latest = max(matching, key=lambda r: (
            str(r.get("created_at") or ""),
            int(r.get("run_attempt") or 0),
            int(r.get("id") or 0),
        ))
        _require(
            latest.get("status") == "completed"
            and latest.get("conclusion") == "success",
            f"latest exact-head {event} workflow is not successful: {name}",
        )


def _validate_materializer_and_notes(api: Any, sha: str) -> str:
    package = _contents(api, "pyproject.toml", sha)
    _require("[project]" in package, "release package lacks [project] metadata")
    section = package.split("[project]", 1)[1].split("\n[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', section, re.MULTILINE)
    _require(match is not None and match.group(1) == VERSION,
             "release package version does not equal 0.3.0")

    try:
        manifest = json.loads(_contents(api, "agora.materializer.json", sha))
        materializers = manifest["materializers"]
        _require(len(materializers) == 1, "reviewed release must own one producer")
        item = materializers[0]
        _require(
            manifest["plugin"]["id"] == "cuc-burns"
            and manifest["plugin"]["version"] == VERSION
            and item["id"] == "cuc-burns-csv"
            and item["acquisition"][0]["type"] == "user-local"
            and item["input"]["allow_symlinks"] is False
            and item["parent_input"]["resource"] == "cuc"
            and "0.2.8" in item["parent_input"]["parent_versions"]
            and item["execution"]["module"] == "ugarit_context_parsing.agora_adapter"
            and item["execution"]["network"] == "deny"
            and item["output"]["composition"]["kind"] == "feature-module"
            and item["output"]["composition"]["parent"] == "cuc",
            "release manifest differs from reviewed parent-bound local-only producer",
        )
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise ReleaseGateError("release manifest is invalid or unreviewed") from exc

    notes = _contents(api, "docs/releases/v0.3.0.md", sha)
    _require(
        "# Ugarit Context Parsing v0.3.0" in notes
        and "feature-only" in notes
        and "agora.materializer.json" in notes
        and "No Burns-derived data files are attached to the release." in notes,
        "release notes lack immutable feature-only / licensed-data boundaries",
    )
    return notes


def _tag_commit(api: Any, tag: dict | None) -> str | None:
    if tag is None:
        return None
    _require(tag.get("ref") == f"refs/tags/{TAG}", "unexpected Git tag ref")
    obj = tag.get("object")
    for _ in range(4):
        _require(isinstance(obj, dict), "malformed Git tag object")
        sha, kind = obj.get("sha"), obj.get("type")
        _require(isinstance(sha, str) and _SHA.fullmatch(sha),
                 "invalid SHA in Git tag")
        if kind == "commit":
            return sha
        _require(kind == "tag", "Git tag does not point to a commit")
        annotated = _get(api, f"git/tags/{sha}")
        obj = annotated.get("object") if isinstance(annotated, dict) else None
    raise ReleaseGateError("Git tag dereference exceeds allowed depth")


def _verify_existing_tag(api: Any, sha: str) -> bool:
    tag = _get(api, f"git/ref/tags/{TAG}", allow_missing=True)
    current = _tag_commit(api, tag)
    _require(current is None or current == sha,
             "existing v0.3.0 tag points to an unreviewed commit")
    return current is not None


def _verify_current_master(api: Any, sha: str) -> None:
    branch = _get(api, "git/ref/heads/master")
    _require(
        isinstance(branch, dict)
        and branch.get("ref") == "refs/heads/master"
        and isinstance(branch.get("object"), dict)
        and branch["object"].get("type") == "commit"
        and branch["object"].get("sha") == sha,
        "master moved or no longer points to the confirmed release SHA",
    )


def publish_reviewed_release(
    api: Any, *, repository: str, expected_sha: str, confirmation: str,
    github_ref: str, github_sha: str, publish: bool = False,
) -> dict[str, object]:
    """Validate immutable release evidence; write only with explicit publish=True."""
    _require(repository == REPOSITORY, "release must run in the upstream CTC-TF repo")
    _require(github_ref == "refs/heads/master", "release must run on master only")
    _require(isinstance(expected_sha, str) and _SHA.fullmatch(expected_sha),
             "expected release commit must be a full lowercase SHA")
    _require(
        github_sha == expected_sha
        and confirmation == f"{TAG}@{expected_sha}",
        "typed release confirmation or workflow commit SHA mismatch",
    )

    _verify_current_master(api, expected_sha)
    tree, parents = _tree(api, expected_sha)
    _require(len(parents) == 2 and _SHA.fullmatch(parents[1]),
             "release candidate must be a reviewed two-parent PR merge commit")
    reviewed_head = parents[1]
    reviewed_tree, _ = _tree(api, reviewed_head)
    _require(
        reviewed_tree == tree,
        "release merge tree differs from the independently reviewed PR head tree",
    )

    _latest_successful_workflows(
        api, reviewed_head, event="pull_request", required=EXPECTED_PR_WORKFLOWS,
    )
    _latest_successful_workflows(
        api, expected_sha, event="push", required=frozenset({"Tests"}),
    )
    notes = _validate_materializer_and_notes(api, expected_sha)

    _require(
        _get(api, f"releases/tags/{TAG}", allow_missing=True) is None,
        "GitHub Release v0.3.0 already exists; never overwrite a release",
    )
    tag_exists = _verify_existing_tag(api, expected_sha)
    if not publish:
        return {"commit": expected_sha, "reviewed_head": reviewed_head,
                "tree": tree, "tag": TAG, "published": False,
                "matching_tag_exists": tag_exists}

    # Recheck the only moving input immediately before the first write. A
    # concurrent branch move after this point may still occur; the tag always
    # binds the independently reviewed immutable SHA, never a branch label.
    _verify_current_master(api, expected_sha)
    if not tag_exists:
        api.request("POST", "git/refs", {
            "ref": f"refs/tags/{TAG}", "sha": expected_sha,
        })
    _require(_verify_existing_tag(api, expected_sha),
             "created tag was not visible at the reviewed SHA")

    release_payload = {
        "tag_name": TAG,
        "target_commitish": expected_sha,
        "name": TAG,
        "body": notes,
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False,
    }
    api.request("POST", "releases", release_payload)

    # GitHub Release publication is a separate API write; always verify it.
    published = _get(api, f"releases/tags/{TAG}")
    _require(
        isinstance(published, dict)
        and published.get("tag_name") == TAG
        and published.get("body") == notes
        and published.get("draft") is False
        and published.get("prerelease") is False
        and published.get("assets") == []
        and _verify_existing_tag(api, expected_sha),
        "GitHub Release post-publication verification failed",
    )
    return {"commit": expected_sha, "reviewed_head": reviewed_head,
            "tree": tree, "tag": TAG, "published": True,
            "matching_tag_exists": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--publish", action="store_true",
        help="explicitly create v0.3.0 tag and Release after all gates",
    )
    args = parser.parse_args(argv)
    if not os.environ.get("GH_TOKEN"):
        parser.error("GH_TOKEN is required for the authenticated GitHub API")
    if args.publish and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        parser.error("publication requires a manually dispatched GitHub workflow")

    try:
        result = publish_reviewed_release(
            GitHubCLI(),
            repository=os.environ.get("GITHUB_REPOSITORY", ""),
            expected_sha=os.environ.get("RELEASE_EXPECTED_SHA", ""),
            confirmation=os.environ.get("RELEASE_CONFIRMATION", ""),
            github_ref=os.environ.get("GITHUB_REF", ""),
            github_sha=os.environ.get("GITHUB_SHA", ""),
            publish=args.publish,
        )
    except ReleaseGateError as exc:
        print(f"Release gate denied: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
