"""Keep the documented local CUC acquisition faithful to the reviewed pin."""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

from ugarit_context_parsing.cuc_index import (
    REVIEWED_CUC_COMMIT,
    REVIEWED_CUC_REPOSITORY,
    REVIEWED_CUC_VERSION,
)

README = Path(__file__).resolve().parents[1] / "README.md"


class ReviewedCucQuickstartDocTests(unittest.TestCase):
    def test_copy_paste_quickstart_pins_explicit_upstream_and_real_module_cli(self):
        text = README.read_text(encoding="utf-8")
        match = re.search(
            r"(?ms)^### Local quickstart: reviewed CUC\s*$"
            r".*?^\x60\x60\x60bash\s*$\n(.*?)^\x60\x60\x60\s*$",
            text,
        )
        self.assertIsNotNone(match, "README must include the reviewed-CUC quickstart bash block")
        assert match is not None
        script = match.group(1)

        self.assertEqual(REVIEWED_CUC_REPOSITORY, "DT-UCPH/cuc")
        self.assertIn(f"https://github.com/{REVIEWED_CUC_REPOSITORY}.git", script)
        self.assertIn(REVIEWED_CUC_COMMIT, script)
        self.assertIn("git -C \"$CUC_DIR\" fetch --depth=1 origin", script)
        self.assertIn('git -C "$CUC_DIR" checkout --detach FETCH_HEAD', script)
        self.assertIn(f'tf/{REVIEWED_CUC_VERSION}', script)
        self.assertIn('CUC_TF="$CUC_DIR/tf/0.2.8"', script)

        self.assertIn("python -m pip install .", script)
        self.assertIn('ugarit-context-parsing module "$BURNS_CSV"', script)
        self.assertIn("--input-format csv", script)
        self.assertIn('--cuc "$CUC_TF"', script)
        self.assertIn('--output "$BURNS_MODULE"', script)
        self.assertIn('test ! -e "$BURNS_MODULE"', script)

        syntax = subprocess.run(
            ["bash", "-n"], input=script, capture_output=True, text=True, check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_quickstart_preserves_offline_materialization_and_agora_boundary(self):
        text = README.read_text(encoding="utf-8")
        start = text.find("### Local quickstart: reviewed CUC")
        self.assertNotEqual(start, -1)
        end = text.find("\n### ", start + 4)
        section = text[start:end if end != -1 else None]
        self.assertIn("does not download CUC", section)
        self.assertIn("user-local", section)
        self.assertIn("Agora", section)
        self.assertIn("not", section.lower())


if __name__ == "__main__":
    unittest.main()
