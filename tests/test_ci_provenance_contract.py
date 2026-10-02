from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.check_ci_provenance import parse_commit_parents, validate_provenance


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
RUN_PATTERN = re.compile(
    r"^\s*run:\s*['\"]?python scripts/check_ci_provenance\.py['\"]?\s*(?:#.*)?$",
    re.MULTILINE,
)
CHECKOUT_PATTERN = re.compile(r"actions/checkout@[A-Za-z0-9._/-]+")
JOB_PATTERN = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
BASE = "1" * 40
HEAD = "2" * 40
MERGE = "3" * 40
OTHER = "4" * 40
TREE = "5" * 40


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


def _job_blocks(workflow: str) -> dict[str, str]:
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    in_jobs = False
    for line in workflow.splitlines():
        if line == "jobs:":
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line.startswith(" "):
            break
        match = JOB_PATTERN.match(line)
        if match:
            current = match.group(1)
            jobs[current] = [line]
        elif current is not None:
            jobs[current].append(line)
    return {name: "\n".join(lines) for name, lines in jobs.items()}


def _pull_request_event() -> dict:
    return {
        "pull_request": {
            "base": {"sha": BASE},
            "head": {"sha": HEAD},
        }
    }


class CiProvenanceWorkflowContractTests(unittest.TestCase):
    def test_every_checkout_job_invokes_provenance_checker_exactly_once(self):
        checkout_jobs = 0
        provenance_steps = 0
        for path in _workflow_paths():
            jobs = _job_blocks(path.read_text(encoding="utf-8"))
            for name, block in jobs.items():
                checkout_count = len(CHECKOUT_PATTERN.findall(block))
                provenance_count = len(RUN_PATTERN.findall(block))
                provenance_steps += provenance_count
                if checkout_count:
                    checkout_jobs += 1
                    with self.subTest(workflow=path.name, job=name):
                        self.assertEqual(provenance_count, 1)
                else:
                    with self.subTest(workflow=path.name, job=name):
                        self.assertEqual(provenance_count, 0)

        self.assertGreater(checkout_jobs, 0)
        self.assertEqual(provenance_steps, checkout_jobs)

    def test_reviewed_cuc_consumer_smoke_tracks_all_package_changes(self):
        workflow = (
            WORKFLOWS / "test-reviewed-cuc-burns-entities.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("      - 'src/ugarit_context_parsing/**'", workflow)

    def test_real_source_workflow_tracks_alignment_audit_semantics(self):
        workflow = (
            WORKFLOWS / "test-real-burns-source.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("      - 'scripts/audit_burns_alignment.py'", workflow)

    def test_release_surface_triggers_all_path_filtered_acceptance_workflows(self):
        acceptance = (
            "test-reviewed-cuc-index.yml",
            "test-reviewed-cuc-burns-entities.yml",
            "test-context-fabric-burns-module.yml",
            "test-real-burns-source.yml",
            "test-appendix-cuc-concordance.yml",
        )
        for name in acceptance:
            workflow = (WORKFLOWS / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertIn("      - 'docs/releases/**'", workflow)
                self.assertIn("      - 'tests/test_release_version.py'", workflow)

    def test_job_block_parser_keeps_steps_in_their_own_jobs(self):
        workflow = """jobs:
  alpha:
    steps:
      - uses: actions/checkout@deadbeef
      - name: provenance
        run: python scripts/check_ci_provenance.py
  beta:
    steps:
      - name: ordinary
        run: echo ok
"""
        jobs = _job_blocks(workflow)
        self.assertEqual(set(jobs), {"alpha", "beta"})
        self.assertEqual(len(CHECKOUT_PATTERN.findall(jobs["alpha"])), 1)
        self.assertEqual(len(RUN_PATTERN.findall(jobs["alpha"])), 1)
        self.assertEqual(len(CHECKOUT_PATTERN.findall(jobs["beta"])), 0)
        self.assertEqual(len(RUN_PATTERN.findall(jobs["beta"])), 0)


class CommitObjectParserTests(unittest.TestCase):
    def test_reads_ordered_parents_from_raw_merge_commit(self):
        raw = (
            f"tree {TREE}\n"
            f"parent {BASE}\n"
            f"parent {HEAD}\n"
            "author Example <example@example.com> 0 +0000\n"
            "committer Example <example@example.com> 0 +0000\n"
            "\nMerge\n"
        )
        self.assertEqual(parse_commit_parents(raw), (BASE, HEAD))

    def test_reads_parent_even_when_parent_object_need_not_be_available(self):
        raw = f"tree {TREE}\nparent {BASE}\n\nmessage\n"
        self.assertEqual(parse_commit_parents(raw), (BASE,))

    def test_rejects_missing_tree_header(self):
        with self.assertRaisesRegex(ValueError, "missing tree"):
            parse_commit_parents(f"parent {BASE}\n\nmessage\n")

    def test_rejects_malformed_parent_header(self):
        with self.assertRaisesRegex(ValueError, "commit parent"):
            parse_commit_parents(f"tree {TREE}\nparent not-a-sha\n\nmessage\n")


class CiProvenanceValidatorTests(unittest.TestCase):
    def test_valid_pull_request_merge(self):
        evidence = validate_provenance(
            event_name="pull_request",
            event=_pull_request_event(),
            github_sha=MERGE,
            checked_out_sha=MERGE,
            parents=(BASE, HEAD),
        )
        self.assertEqual(
            evidence,
            {
                "base_sha": BASE,
                "head_sha": HEAD,
                "mode": "pull_request_merge",
                "parents": [BASE, HEAD],
                "tested_sha": MERGE,
            },
        )

    def test_rejects_checkout_different_from_github_sha(self):
        with self.assertRaisesRegex(ValueError, "does not match GITHUB_SHA"):
            validate_provenance(
                event_name="pull_request",
                event=_pull_request_event(),
                github_sha=MERGE,
                checked_out_sha=OTHER,
                parents=(BASE, HEAD),
            )

    def test_rejects_non_merge_parent_count(self):
        with self.assertRaisesRegex(ValueError, "exactly two parents"):
            validate_provenance(
                event_name="pull_request",
                event=_pull_request_event(),
                github_sha=MERGE,
                checked_out_sha=MERGE,
                parents=(HEAD,),
            )

    def test_rejects_wrong_parent_order(self):
        with self.assertRaisesRegex(ValueError, "do not match event base/head"):
            validate_provenance(
                event_name="pull_request",
                event=_pull_request_event(),
                github_sha=MERGE,
                checked_out_sha=MERGE,
                parents=(HEAD, BASE),
            )

    def test_rejects_missing_pull_request_fields(self):
        with self.assertRaisesRegex(ValueError, "missing head/base"):
            validate_provenance(
                event_name="pull_request",
                event={"pull_request": {"head": {"sha": HEAD}}},
                github_sha=MERGE,
                checked_out_sha=MERGE,
                parents=(BASE, HEAD),
            )

    def test_valid_push(self):
        evidence = validate_provenance(
            event_name="push",
            event={},
            github_sha=HEAD,
            checked_out_sha=HEAD,
            parents=(BASE,),
        )
        self.assertEqual(evidence, {"mode": "push", "tested_sha": HEAD})

    def test_push_rejects_checkout_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not match GITHUB_SHA"):
            validate_provenance(
                event_name="push",
                event={},
                github_sha=HEAD,
                checked_out_sha=OTHER,
                parents=(BASE,),
            )

    def test_rejects_unsupported_event(self):
        with self.assertRaisesRegex(ValueError, "unsupported GitHub event"):
            validate_provenance(
                event_name="workflow_dispatch",
                event={},
                github_sha=HEAD,
                checked_out_sha=HEAD,
                parents=(BASE,),
            )


if __name__ == "__main__":
    unittest.main()
