"""Path safety for explicitly requested, restricted Burns audit reports."""
from __future__ import annotations

import io
import json
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import audit_burns_alignment as audit
from test_headword_candidate_research import _index, _record


class AuditPrivateOutputPolicyTests(unittest.TestCase):
    def _run(self, checkout: Path, workbooks: Path, cuc: Path, *options: str) -> str:
        record = _record(1, 'secret alpha hidden', 10)
        index = _index({10: ('hidden', 'alphax', 'secret')})
        stdout = io.StringIO()
        with (
            patch.object(audit, 'ROOT', checkout),
            patch.object(audit, 'load_pdf_directory',
                         return_value=SimpleNamespace(files=('synthetic.pdf',), records=(record,))),
            patch.object(audit, 'build_reviewed_cuc_index', return_value=index),
            patch.object(audit, 'ensure', side_effect=AssertionError('unexpected download')),
            redirect_stdout(stdout),
        ):
            self.assertEqual(audit.main([
                '--workbooks', str(workbooks), '--cuc', str(cuc), *options,
            ]), 0)
        return stdout.getvalue()

    def _roots(self, root: Path):
        checkout = root / 'software'
        workbooks = root / 'Workbooks'
        cuc = root / 'cuc' / 'tf' / '0.2.8'
        for directory in (checkout, workbooks, cuc):
            directory.mkdir(parents=True)
        return checkout, workbooks, cuc

    def test_legacy_report_refuses_checkout_workbooks_cuc_and_symlink_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkout, workbooks, cuc = self._roots(root)
            alias = root / 'cuc-alias'
            alias.symlink_to(cuc, target_is_directory=True)
            forbidden = (
                checkout / 'private.json',
                workbooks / 'private.json',
                cuc / 'otype.tf',
                alias / 'oslots.tf',
            )
            for target in forbidden:
                target.write_text('ORIGINAL', encoding='utf-8')
                with self.subTest(target=target):
                    with self.assertRaisesRegex(ValueError, 'overlaps'):
                        self._run(checkout, workbooks, cuc, '--report', str(target))
                    self.assertEqual(target.read_text(encoding='utf-8'), 'ORIGINAL')

    def test_two_report_options_may_not_target_same_resolved_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkout, workbooks, cuc = self._roots(root)
            outside = root / 'private'
            outside.mkdir()
            alias = root / 'private-alias'
            alias.symlink_to(outside, target_is_directory=True)
            target = outside / 'review.json'
            target.write_text('ORIGINAL', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'same destination'):
                self._run(
                    checkout, workbooks, cuc,
                    '--report', str(target),
                    '--private-out-of-order', str(alias / 'review.json'),
                )
            self.assertEqual(target.read_text(encoding='utf-8'), 'ORIGINAL')

    def test_two_distinct_outside_reports_keep_existing_schemas_0600_and_safe_stdout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkout, workbooks, cuc = self._roots(root)
            first = root / 'private' / 'alignments.json'
            second = root / 'private' / 'cases.json'
            output = self._run(
                checkout, workbooks, cuc,
                '--report', str(first),
                '--private-out-of-order', str(second),
                '--research-multitoken',
            )
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(second.stat().st_mode), 0o600)
            self.assertEqual(json.loads(first.read_text(encoding='utf-8'))['schema'],
                             'burns-cuc-alignment-report-v1')
            self.assertEqual(json.loads(second.read_text(encoding='utf-8'))['schema'],
                             'burns-private-out-of-order-v1')
            self.assertEqual(json.loads(second.read_text(encoding='utf-8'))['occurrences'], 1)
            stats = json.loads(output)
            self.assertEqual(stats['multitoken_residual_research']['out_of_order_research']['occurrences'], 1)
            for restricted in ('secret alpha hidden', 'KTU 1.14', str(first), str(second)):
                self.assertNotIn(restricted, output)


if __name__ == '__main__':
    unittest.main()
