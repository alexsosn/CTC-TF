"""Keep reviewed-CUC acquisition and the module CLI copy-paste coherent.

Only inspects README/source metadata; never downloads CUC or licensed Burns data.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
import unittest

from ugarit_context_parsing.cuc_index import (
    REVIEWED_CUC_COMMIT,
    REVIEWED_CUC_REPOSITORY,
    REVIEWED_CUC_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SECTION_HEADING = "## Feature-only module over reviewed CUC\n"
QUICKSTART_HEADING = "### Quickstart with the exact reviewed CUC"


def _materialization_section() -> str:
    readme = README.read_text(encoding="utf-8")
    if SECTION_HEADING not in readme:
        raise AssertionError("README lacks current feature-only CUC module section")
    return readme.split(SECTION_HEADING, 1)[1].split("\n## ", 1)[0]


def _quickstart_script() -> str:
    section = _materialization_section()
    match = re.search(
        rf"(?ms)^{re.escape(QUICKSTART_HEADING)}\s*$"
        r".*?^`{3}bash\s*$\n(.*?)^`{3}\s*$",
        section,
    )
    if match is None:
        raise AssertionError("README lacks runnable exact-CUC quickstart bash block")
    return match.group(1)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class ReviewedCucQuickstartDocumentationTests(unittest.TestCase):
    def test_quickstart_pins_canonical_cuc_checkout_not_moving_main(self):
        section = _materialization_section()
        script = _quickstart_script()
        normalized = _normalized(script)
        remote = f"https://github.com/{REVIEWED_CUC_REPOSITORY}.git"

        self.assertIn("python -m pip install .", script)
        self.assertIn(f'git clone --filter=blob:none --no-checkout {remote} "$CUC_DIR"', normalized)
        self.assertIn(
            f'git -C "$CUC_DIR" checkout --detach {REVIEWED_CUC_COMMIT}',
            normalized,
        )
        self.assertIn('git -C "$CUC_DIR" rev-parse HEAD', script)
        self.assertIn(REVIEWED_CUC_COMMIT, section)
        self.assertIn(f'tf/{REVIEWED_CUC_VERSION}', script)
        self.assertNotIn("git clone --depth", normalized)
        self.assertNotIn(f"fetch --depth 1 origin {REVIEWED_CUC_COMMIT}", normalized)
        self.assertNotIn("checkout --detach FETCH_HEAD", normalized)

    def test_actual_cli_and_absent_output_are_copy_paste_coherent(self):
        script = _quickstart_script()
        normalized = _normalized(script)
        self.assertIn("ugarit-context-parsing module output", normalized)
        self.assertIn("--input-format csv", normalized)
        self.assertIn('--cuc "$CUC_TF"', normalized)
        self.assertIn('--output "$BURNS_MODULE"', normalized)
        self.assertIn('test ! -e "$BURNS_MODULE"', normalized)
        syntax = subprocess.run(
            ["bash", "-n"], input=script, capture_output=True, text=True, check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_quickstart_does_not_create_unignored_corpora_inside_software_repo(self):
        script = _quickstart_script()
        normalized = _normalized(script)
        self.assertIn('CUC_DIR="$HOME/data/cuc-reviewed"', script)
        self.assertIn('BURNS_MODULE="$HOME/data/burns-feature-module"', script)
        self.assertIn('git clone --filter=blob:none --no-checkout', script)
        self.assertIn('"$CUC_DIR"', script)
        self.assertIn('--cuc "$CUC_TF"', normalized)
        self.assertIn('--output "$BURNS_MODULE"', normalized)
        self.assertNotIn(f"https://github.com/{REVIEWED_CUC_REPOSITORY}.git cuc", normalized)
        self.assertNotIn("--output tf/burns-module", normalized)
        self.assertIn("set -eu", script)
        self.assertIn("test ! -e \"$BURNS_MODULE\"", script)

    def test_converter_source_and_agora_boundaries_remain_explicit(self):
        readme = README.read_text(encoding="utf-8")
        section = _materialization_section().casefold()
        agora = readme.split("### Agora status\n", 1)[1].split("\n### ", 1)[0].casefold()

        self.assertIn("does not download cuc", section)
        self.assertNotIn("## materializing a cuc-aligned burns feature module", section)
        self.assertIn("user-local", section)
        self.assertIn("cuc-burns", agora)
        self.assertIn("local-module", agora)
        self.assertIn("fully managed execution", agora)
        self.assertIn("remains tracked", agora)
        self.assertNotIn("standalone row-slot materializers are registered", agora)


if __name__ == "__main__":
    unittest.main()
