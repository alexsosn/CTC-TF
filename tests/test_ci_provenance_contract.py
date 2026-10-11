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
            WORKFLOWS / "test-reviewed-cuc-burns-feature-module.yml"
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
            "test-reviewed-cuc-burns-feature-module.yml",
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

    def test_manual_workflow_dispatch_attests_exact_checkout(self):
        evidence = validate_provenance(
            event_name="workflow_dispatch",
            event={"inputs": {"release_confirmation": "synthetic"}},
            github_sha=HEAD,
            checked_out_sha=HEAD,
            parents=(BASE,),
        )
        self.assertEqual(
            evidence,
            {"mode": "workflow_dispatch", "tested_sha": HEAD},
        )

    def test_manual_workflow_dispatch_rejects_checkout_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not match GITHUB_SHA"):
            validate_provenance(
                event_name="workflow_dispatch",
                event={},
                github_sha=HEAD,
                checked_out_sha=OTHER,
                parents=(BASE,),
            )

    def test_rejects_unsupported_event(self):
        with self.assertRaisesRegex(ValueError, "unsupported GitHub event"):
            validate_provenance(
                event_name="schedule",
                event={},
                github_sha=HEAD,
                checked_out_sha=HEAD,
                parents=(BASE,),
            )


ADVANCED_BASE = "6" * 40


def _stale_base_event() -> dict:
    event = _pull_request_event()
    event["number"] = 17
    event["pull_request"]["number"] = 17
    event["pull_request"]["base"]["ref"] = "master"
    event["pull_request"]["base"]["repo"] = {"full_name": "alexsosn/CTC-TF"}
    return event


class AdvancedBaseProvenanceTests(unittest.TestCase):
    def test_legitimate_advanced_base_requires_proven_target_history(self):
        calls = []

        def trusted(event_base, actual_base, base_ref):
            calls.append((event_base, actual_base, base_ref))
            return True

        evidence = validate_provenance(
            event_name="pull_request",
            event=_stale_base_event(),
            github_sha=MERGE,
            checked_out_sha=MERGE,
            parents=(ADVANCED_BASE, HEAD),
            github_ref="refs/pull/17/merge",
            advanced_base_verifier=trusted,
        )
        self.assertEqual(calls, [(BASE, ADVANCED_BASE, "master")])
        self.assertEqual(evidence["tested_sha"], MERGE)
        self.assertEqual(evidence["head_sha"], HEAD)
        self.assertEqual(evidence["base_sha"], BASE)
        self.assertEqual(evidence["parents"], [ADVANCED_BASE, HEAD])
        self.assertEqual(evidence["base_validation"], "verified_advanced_base")

    def test_advanced_base_denies_forged_parent_or_merge_ref(self):
        kwargs = dict(
            event_name="pull_request", event=_stale_base_event(),
            github_sha=MERGE, checked_out_sha=MERGE,
            parents=(ADVANCED_BASE, HEAD),
            github_ref="refs/pull/17/merge",
        )
        with self.assertRaisesRegex(ValueError, "base"):
            validate_provenance(
                **kwargs, advanced_base_verifier=lambda *_: False
            )
        with self.assertRaisesRegex(ValueError, "ref"):
            validate_provenance(
                **{**kwargs, "github_ref": "refs/heads/master"},
                advanced_base_verifier=lambda *_: True,
            )
        with self.assertRaisesRegex(ValueError, "head|parents"):
            validate_provenance(
                **{**kwargs, "parents": (ADVANCED_BASE, OTHER)},
                advanced_base_verifier=lambda *_: True,
            )

    def test_advanced_base_is_denied_when_no_verifier_supplied(self):
        with self.assertRaisesRegex(ValueError, "base/head"):
            validate_provenance(
                event_name="pull_request", event=_stale_base_event(),
                github_sha=MERGE, checked_out_sha=MERGE,
                parents=(ADVANCED_BASE, HEAD),
            )

    def test_rest_proof_rejects_wrong_ancestry_and_accepts_valid_history(self):
        import json
        from unittest.mock import patch
        from scripts.check_ci_provenance import verify_advanced_pr_base

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(self.payload).encode()

        def compare(base, status="ahead", behind=0):
            return {
                "status": status, "behind_by": behind,
                "base_commit": {"sha": base},
                "merge_base_commit": {"sha": base},
            }

        responses = [
            compare(BASE),
            {"object": {"sha": OTHER, "type": "commit"}},
            compare(ADVANCED_BASE),
        ]
        with patch(
            "scripts.check_ci_provenance.urllib.request.urlopen",
            side_effect=[FakeResponse(payload) for payload in responses],
        ) as get:
            self.assertTrue(verify_advanced_pr_base(
                repository="alexsosn/CTC-TF",
                base_ref="master",
                event_base_sha=BASE,
                actual_base_sha=ADVANCED_BASE,
                token="synthetic-readonly-token",
            ))
            self.assertEqual(get.call_count, 3)
            urls = [call.args[0].full_url for call in get.call_args_list]
            self.assertIn(f"{BASE}...{ADVANCED_BASE}", urls[0])
            self.assertIn("/git/ref/heads/master", urls[1])
            self.assertIn(f"{ADVANCED_BASE}...{OTHER}", urls[2])
            self.assertNotIn("synthetic-readonly-token", "".join(urls))

        # The target must be a branch pointing directly at a commit.
        # A malformed ref payload lacking its object type is NOT proof.
        malformed = [
            compare(BASE),
            {"object": {"sha": OTHER}},
            compare(ADVANCED_BASE),
        ]
        with patch(
            "scripts.check_ci_provenance.urllib.request.urlopen",
            side_effect=[FakeResponse(payload) for payload in malformed],
        ):
            self.assertFalse(verify_advanced_pr_base(
                repository="alexsosn/CTC-TF",
                base_ref="master",
                event_base_sha=BASE,
                actual_base_sha=ADVANCED_BASE,
                token="synthetic-readonly-token",
            ))

        for bad_response in (
            compare(BASE, "behind", behind=2),
            compare(BASE, "diverged", behind=1),
            {"status": "ahead", "merge_base_commit": {"sha": OTHER}},
        ):
            with self.subTest(bad_response=bad_response), patch(
                "scripts.check_ci_provenance.urllib.request.urlopen",
                return_value=FakeResponse(bad_response),
            ):
                self.assertFalse(verify_advanced_pr_base(
                    repository="alexsosn/CTC-TF",
                    base_ref="master",
                    event_base_sha=BASE,
                    actual_base_sha=ADVANCED_BASE,
                    token="synthetic-readonly-token",
                ))

    def test_provenance_workflows_inject_readonly_token_explicitly(self):
        for path in _workflow_paths():
            text = path.read_text(encoding="utf-8")
            if "python scripts/check_ci_provenance.py" not in text:
                continue
            with self.subTest(workflow=path.name):
                if path.name == "publish-reviewed-v0.3.0.yml":
                    # workflow_dispatch/push never needs PR ancestry network proof;
                    # publisher's token has contents:write and must not be exposed.
                    self.assertNotIn("GH_TOKEN:", text)
                else:
                    self.assertIn("GH_TOKEN: ${{ github.token }}", text)


if __name__ == "__main__":
    unittest.main()
