#!/usr/bin/env python3
"""Attest the exact Git revision exercised by GitHub Actions."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


_SHA = re.compile(r"^[0-9a-f]{40}$")


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(f"{label} must be a 40-character lowercase Git SHA")
    return value


def parse_commit_parents(raw_commit: str) -> tuple[str, ...]:
    """Read ordered parent IDs from raw commit-object headers."""

    parents: list[str] = []
    saw_tree = False
    for line in raw_commit.splitlines():
        if not line:
            break
        if line.startswith("tree "):
            if saw_tree:
                raise ValueError("commit object contains multiple tree headers")
            _require_sha(line.removeprefix("tree "), "commit tree")
            saw_tree = True
        elif line.startswith("parent "):
            parents.append(_require_sha(line.removeprefix("parent "), "commit parent"))
    if not saw_tree:
        raise ValueError("commit object is missing tree header")
    return tuple(parents)


_GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_GITHUB_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


def _github_json(url: str, token: str) -> dict[str, Any]:
    """Fetch read-only provider evidence; fail closed without leaking credentials."""
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            document = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("GitHub ancestry API lookup failed closed") from exc
    if not isinstance(document, dict):
        raise ValueError("GitHub ancestry API returned a non-object response")
    return document


def _confirms_ancestor(document: dict[str, Any], base_sha: str) -> bool:
    """An actual ancestor has no commits behind and is the merge-base."""
    base = document.get("base_commit")
    merge_base = document.get("merge_base_commit")
    return (
        document.get("status") in {"ahead", "identical"}
        and document.get("behind_by") == 0
        and isinstance(base, dict)
        and isinstance(merge_base, dict)
        and base.get("sha") == base_sha
        and merge_base.get("sha") == base_sha
    )


def verify_advanced_pr_base(
    *,
    repository: str,
    base_ref: str,
    event_base_sha: str,
    actual_base_sha: str,
    token: str,
) -> bool:
    """Prove an advanced PR merge parent is in the *authentic base branch* history.

    The event base must be an ancestor of the merge's first parent, AND the
    latter must be an ancestor of the currently trusted base branch tip.
    No network fallback, no accepting merely syntactically valid SHAs.
    """
    event_base_sha = _require_sha(event_base_sha, "event base")
    actual_base_sha = _require_sha(actual_base_sha, "synthetic merge first parent")
    if not isinstance(repository, str) or not _GITHUB_REPOSITORY.fullmatch(repository):
        raise ValueError("invalid GitHub repository for provenance verification")
    if (
        not isinstance(base_ref, str)
        or not _GITHUB_BRANCH.fullmatch(base_ref)
        or base_ref.startswith(("/", "."))
        or ".." in base_ref
        or "//" in base_ref
    ):
        raise ValueError("invalid GitHub base branch for provenance verification")
    if not isinstance(token, str) or not token:
        raise ValueError("read-only GitHub token is required to verify advanced PR base")

    endpoint = f"https://api.github.com/repos/{repository}"
    before = _github_json(
        f"{endpoint}/compare/{event_base_sha}...{actual_base_sha}", token
    )
    if not _confirms_ancestor(before, event_base_sha):
        return False

    current_ref = _github_json(
        f"{endpoint}/git/ref/heads/{urllib.parse.quote(base_ref, safe='/')}",
        token,
    )
    current_obj = current_ref.get("object")
    if not isinstance(current_obj, dict) or current_obj.get("type") != "commit":
        return False
    current_tip = _require_sha(current_obj.get("sha"), "live GitHub base ref")
    after = _github_json(
        f"{endpoint}/compare/{actual_base_sha}...{current_tip}", token
    )
    return _confirms_ancestor(after, actual_base_sha)


def validate_provenance(
    *,
    event_name: str,
    event: dict[str, Any],
    github_sha: str,
    checked_out_sha: str,
    parents: tuple[str, ...],
    github_ref: str | None = None,
    advanced_base_verifier: Callable[[str, str, str], bool] | None = None,
) -> dict[str, Any]:
    """Validate CI checkout provenance and return canonical evidence data."""

    github_sha = _require_sha(github_sha, "GITHUB_SHA")
    checked_out_sha = _require_sha(checked_out_sha, "checked-out HEAD")
    if checked_out_sha != github_sha:
        raise ValueError(
            f"checked-out HEAD {checked_out_sha} does not match GITHUB_SHA {github_sha}"
        )

    if event_name == "pull_request":
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict):
            raise ValueError("pull_request event payload is missing pull_request")
        head = pull_request.get("head")
        base = pull_request.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise ValueError("pull_request event payload is missing head/base objects")
        head_sha = _require_sha(head.get("sha"), "pull_request.head.sha")
        base_sha = _require_sha(base.get("sha"), "pull_request.base.sha")
        normalized_parents = tuple(
            _require_sha(parent, f"merge parent {index}")
            for index, parent in enumerate(parents, start=1)
        )
        if len(normalized_parents) != 2:
            raise ValueError(
                "pull_request merge checkout must have exactly two parents, got "
                f"{len(normalized_parents)}"
            )
        expected = (base_sha, head_sha)
        if normalized_parents[0] == normalized_parents[1] or normalized_parents[1] != head_sha:
            raise ValueError(
                "pull_request merge parents do not match event base/head: "
                f"expected {expected!r}, got {normalized_parents!r}"
            )
        advanced = normalized_parents[0] != base_sha
        if advanced and advanced_base_verifier is None:
            raise ValueError(
                "pull_request merge parents do not match event base/head "
                "and advanced base ancestry was not verified"
            )
        if advanced:
            number = pull_request.get("number")
            if (
                not isinstance(number, int) or isinstance(number, bool)
                or number <= 0 or event.get("number") != number
            ):
                raise ValueError("advanced pull_request merge has invalid PR number")
            if github_ref != f"refs/pull/{number}/merge":
                raise ValueError("advanced pull_request merge ref does not match PR number")
            base_ref = base.get("ref")
            if not isinstance(base_ref, str) or not base_ref:
                raise ValueError("advanced pull_request merge is missing target base ref")
            if (
                advanced_base_verifier is None
                or not advanced_base_verifier(base_sha, normalized_parents[0], base_ref)
            ):
                raise ValueError(
                    "pull_request merge parents do not match event base/head "
                    "and advanced base ancestry was not verified"
                )
        evidence = {
            "base_sha": base_sha,
            "head_sha": head_sha,
            "mode": "pull_request_merge",
            "parents": list(normalized_parents),
            "tested_sha": checked_out_sha,
        }
        if advanced:
            evidence["base_validation"] = "verified_advanced_base"
        return evidence

    if event_name in ("push", "workflow_dispatch"):
        # Manual, repository-owned release workflows check out the dispatch
        # commit, not a synthetic PR merge. The release publisher separately
        # validates the master ref and exact reviewed merge tree/CI.
        for index, parent in enumerate(parents, start=1):
            _require_sha(parent, f"{event_name} parent {index}")
        return {
            "mode": event_name,
            "tested_sha": checked_out_sha,
        }

    raise ValueError(f"unsupported GitHub event for provenance validation: {event_name!r}")


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def main() -> None:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    github_sha = os.environ.get("GITHUB_SHA", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is required")

    with Path(event_path).open(encoding="utf-8") as handle:
        event = json.load(handle)
    if not isinstance(event, dict):
        raise ValueError("GitHub event payload must be a JSON object")

    checked_out_sha = _git("rev-parse", "HEAD")
    raw_commit = _git("cat-file", "-p", "HEAD")
    parents = parse_commit_parents(raw_commit)
    def _verify_event_base(event_base: str, actual_base: str, base_ref: str) -> bool:
        pull = event.get("pull_request")
        base = pull.get("base") if isinstance(pull, dict) else None
        base_repo = base.get("repo") if isinstance(base, dict) else None
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if not isinstance(base_repo, dict) or base_repo.get("full_name") != repo:
            raise ValueError("advanced PR base repository differs from trusted CI repository")
        return verify_advanced_pr_base(
            repository=repo,
            base_ref=base_ref,
            event_base_sha=event_base,
            actual_base_sha=actual_base,
            token=os.environ.get("GH_TOKEN", ""),
        )

    evidence = validate_provenance(
        event_name=event_name,
        event=event,
        github_sha=github_sha,
        checked_out_sha=checked_out_sha,
        parents=parents,
        github_ref=os.environ.get("GITHUB_REF", ""),
        advanced_base_verifier=_verify_event_base,
    )
    print(
        "ci_provenance="
        + json.dumps(
            evidence,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
