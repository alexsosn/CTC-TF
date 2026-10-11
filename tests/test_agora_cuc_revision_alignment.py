"""Enforce exact reviewed CUC commit across the real Agora host acceptance path.

All assertions inspect software/test source only; no licensed Workbooks or
derived artifacts are embedded or loaded by this test.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

from ugarit_context_parsing.cuc_index import REVIEWED_CUC_COMMIT


ROOT = Path(__file__).resolve().parents[1]


class AgoraCucRevisionAlignmentTests(unittest.TestCase):
    def test_real_agora_workflow_checks_out_exact_reviewed_cuc_commit(self):
        workflow = (
            ROOT / ".github" / "workflows" / "test-real-burns-source.yml"
        ).read_text(encoding="utf-8")
        refs = re.findall(
            r"repository:\s*DT-UCPH/cuc\s*\n\s*ref:\s*([0-9a-f]{40})",
            workflow,
        )
        self.assertEqual(refs, [REVIEWED_CUC_COMMIT])

    def test_trusted_parent_receipt_revision_matches_reviewed_cuc_commit(self):
        script = (
            ROOT / "scripts" / "check_agora_burns_parent_binding.py"
        ).read_text(encoding="utf-8")
        assignments = [
            node.value.value
            for node in ast.parse(script).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "CUC_RELEASE"
                for target in node.targets
            )
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ]
        self.assertEqual(assignments, [REVIEWED_CUC_COMMIT])


if __name__ == "__main__":
    unittest.main()
