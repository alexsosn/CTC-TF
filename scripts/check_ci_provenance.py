#!/usr/bin/env python3
"""Attest the exact Git revision exercised by GitHub Actions."""

from __future__ import annotations

import json
import os
import re
import subprocess
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


def validate_provenance(
    *,
    event_name: str,
    event: dict[str, Any],
    github_sha: str,
    checked_out_sha: str,
    parents: tuple[str, ...],
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
        if normalized_parents != expected:
            raise ValueError(
                "pull_request merge parents do not match event base/head: "
                f"expected {expected!r}, got {normalized_parents!r}"
            )
        return {
            "base_sha": base_sha,
            "head_sha": head_sha,
            "mode": "pull_request_merge",
            "parents": list(normalized_parents),
            "tested_sha": checked_out_sha,
        }

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
    evidence = validate_provenance(
        event_name=event_name,
        event=event,
        github_sha=github_sha,
        checked_out_sha=checked_out_sha,
        parents=parents,
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
