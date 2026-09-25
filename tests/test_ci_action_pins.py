from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path


WORKFLOW_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
USES_PATTERN = re.compile(
    r"^\s*(?:-\s*)?uses:\s*(?P<quote>['\"]?)"
    r"(?P<ref>actions/(?:checkout|setup-python)@[A-Za-z0-9._/-]+)"
    r"(?P=quote)\s*(?:#.*)?$",
    re.MULTILINE,
)


def _action_refs(workflow: str) -> list[str]:
    return [match.group("ref") for match in USES_PATTERN.finditer(workflow)]


def _workflow_paths() -> list[Path]:
    return sorted({*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")})


class CiActionPinTests(unittest.TestCase):
    def test_extractor_handles_quoted_refs_and_ignores_comments(self):
        workflow = """
          - uses: actions/checkout@v4
          - uses: 'actions/setup-python@v5'
          - uses: "actions/checkout@deadbeef" # reviewed example
          # - uses: actions/setup-python@ignored
          - run: echo actions/checkout@not-a-uses-line
        """
        self.assertEqual(
            _action_refs(workflow),
            [
                "actions/checkout@v4",
                "actions/setup-python@v5",
                "actions/checkout@deadbeef",
            ],
        )

    def test_checkout_and_setup_python_use_reviewed_immutable_releases(self):
        paths = _workflow_paths()
        self.assertTrue(paths, "no GitHub Actions workflows found")
        actual = Counter(
            ref
            for path in paths
            for ref in _action_refs(path.read_text(encoding="utf-8"))
        )
        # Baseline + synthetic reviewed-CUC native test: 13 checkout / 6 setup.
        # Ephemeral real Burns and Appendix concordance gates each add
        # producer/CUC checkouts plus one setup-python action.
        expected = Counter({CHECKOUT: 17, SETUP_PYTHON: 8})
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
