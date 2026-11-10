"""Local-only source-case diagnostics: never publish the generated private data."""
from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import audit_burns_alignment as audit
from test_headword_candidate_research import _index, _record
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class PrivateOutOfOrderReviewTests(unittest.TestCase):
    def _fixture(self):
        repeated = replace(_record(1, 'secret alpha hidden', 10), references='I.10, 20')
        records = (
            repeated,
            _record(2, 'delta echo foxtrot', 30),
            _record(3, 'g h', 40),       # in-order/no residual
            _record(4, 'i j', 50),       # all exact words, reordered
            _record(5, 'o p', 60),       # exact neighbor: excluded
            _record(6, 'q r', 80),       # token-boundary: excluded
            _record(7, 'x y', 90),       # no exact hits
        )
        index = _index({
            10: ('hidden', 'alphax', 'secret'),
            20: ('hidden', 'x', 'secret'),
            30: ('foxtrot', 'x', 'delta'),
            40: ('g', 'h'),
            50: ('j', 'i'),
            60: ('wrong',), 61: ('o', 'p'),
            80: ('qr',),
            90: ('wrong', 'other'),
        })
        source = normalize_workbook_records(records)
        return records, source, index, align_burns_source(source, index)

    def test_private_cases_match_existing_aggregate_without_promoting_lexical_matches(self):
        _records, source, index, alignments = self._fixture()
        result = audit.private_out_of_order_review(
            source=source, alignments=alignments, index=index,
        )
        stats = audit.aggregate_multitoken_residual_research(
            source=source, alignments=alignments, index=index,
        )['out_of_order_research']
        self.assertEqual(result['schema'], 'burns-private-out-of-order-v1')
        self.assertEqual(result['occurrences'], stats['occurrences'])
        self.assertEqual(result['distinct_annotations'], stats['distinct_annotations'])
        self.assertEqual(result['occurrences'], 4)
        self.assertEqual(result['distinct_annotations'], 3)
        self.assertEqual([case['presence_mask'] for case in result['cases']],
                         ['101', '101', '101', '11'])
        self.assertEqual(result['cases'][0]['burns_tokens'], ['secret', 'alpha', 'hidden'])
        self.assertEqual(result['cases'][0]['cuc_g_cons'], ['hidden', 'alphax', 'secret'])
        self.assertEqual(result['cases'][0]['target'],
                         {'tablet': 'KTU 1.14', 'column': 'I', 'line': 10})
        self.assertEqual(result['cases'][0]['source_reference'], 'I.10, 20')
        self.assertEqual(result['cases'][0]['headword'], 'secret alpha hidden')
        self.assertEqual(result['cases'][0]['annotation_id'], result['cases'][1]['annotation_id'])
        self.assertNotEqual(result['cases'][0]['occurrence_id'], result['cases'][1]['occurrence_id'])
        self.assertTrue(all(case['target']['line'] not in {40, 60, 80, 90}
                            for case in result['cases']))

    def test_cli_explicit_private_output_is_owner_only_and_stdout_safe(self):
        records, source, index, alignments = self._fixture()
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / 'private-review.json'
            args = ['--workbooks', '/synthetic/Workbooks', '--cuc', '/synthetic/cuc',
                    '--private-out-of-order', str(private), '--research-multitoken']
            out = io.StringIO()
            with (
                patch.object(audit, 'load_pdf_directory',
                             return_value=SimpleNamespace(files=('synthetic.pdf',), records=records)),
                patch.object(audit, 'build_reviewed_cuc_index', return_value=index),
                patch.object(audit, 'ensure', side_effect=AssertionError('no download')),
                redirect_stdout(out),
            ):
                self.assertEqual(audit.main(args), 0)
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o600)
            content = json.loads(private.read_text(encoding='utf-8'))
            self.assertEqual(content['occurrences'], 4)
            self.assertEqual(content['distinct_annotations'], 3)
            self.assertIn('secret alpha hidden', private.read_text(encoding='utf-8'))
            self.assertNotIn('secret alpha hidden', out.getvalue())
            self.assertNotIn('KTU 1.14', out.getvalue())
            self.assertNotIn(source.annotations[0].annotation_id, out.getvalue())
            self.assertNotIn(str(private), out.getvalue())
            self.assertEqual(json.loads(out.getvalue())['multitoken_residual_research']
                             ['out_of_order_research']['occurrences'], 4)

    def test_default_cli_never_writes_private_case_report(self):
        records, _source, index, _alignments = self._fixture()
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with (
                patch.object(audit, 'load_pdf_directory',
                             return_value=SimpleNamespace(files=('synthetic.pdf',), records=records)),
                patch.object(audit, 'build_reviewed_cuc_index', return_value=index),
                patch.object(audit, 'ensure', side_effect=AssertionError('no download')),
                patch.object(audit, '_write_private_report') as writer,
                redirect_stdout(out),
            ):
                self.assertEqual(audit.main(['--workbooks', '/synthetic/Workbooks',
                                             '--cuc', '/synthetic/cuc']), 0)
                writer.assert_not_called()
            self.assertEqual(json.loads(out.getvalue())['source']['annotations'], 7)
            self.assertEqual(list(Path(tmp).iterdir()), [])


    def test_private_report_rejects_checkout_source_and_cuc_output_overlap(self):
        records, _source, index, _alignments = self._fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = root / 'checkout'
            workbooks = root / 'Workbooks'
            cuc = root / 'cuc' / 'tf' / '0.2.8'
            for directory in (checkout, workbooks, cuc):
                directory.mkdir(parents=True)
            alias = root / 'cuc-alias'
            alias.symlink_to(cuc, target_is_directory=True)
            forbidden_destinations = (
                checkout / 'private.json',
                workbooks / 'private.json',
                cuc / 'otype.tf',
                alias / 'oslots.tf',
            )
            for destination in forbidden_destinations:
                with (
                    self.subTest(destination=destination),
                    patch.object(audit, 'ROOT', checkout),
                    patch.object(audit, 'load_pdf_directory',
                                 return_value=SimpleNamespace(files=('synthetic.pdf',), records=records)),
                    patch.object(audit, 'build_reviewed_cuc_index', return_value=index),
                    patch.object(audit, 'ensure', side_effect=AssertionError('no download')),
                    redirect_stdout(io.StringIO()),
                ):
                    with self.assertRaisesRegex(ValueError, 'overlaps'):
                        audit.main([
                            '--workbooks', str(workbooks),
                            '--cuc', str(cuc),
                            '--private-out-of-order', str(destination),
                        ])
                    self.assertFalse(destination.exists())

if __name__ == '__main__':
    unittest.main()
