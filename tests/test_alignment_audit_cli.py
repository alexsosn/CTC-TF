"""Opt-in source-safe CLI research, with synthetic private-looking data only."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from scripts import audit_burns_alignment as audit
from test_headword_candidate_research import _index, _record
from ugarit_context_parsing.alignment import align_burns_source
from ugarit_context_parsing.annotations import normalize_workbook_records


class AuditMultitokenCliTests(unittest.TestCase):
    def _run_cli(self, *, research: bool, headword: str, values: tuple[str, ...]):
        record = _record(1, headword, 10)
        index = _index({10: values})
        source = normalize_workbook_records((record,))
        alignments = align_burns_source(source, index)
        pdf = SimpleNamespace(files=("synthetic.pdf",), records=(record,))
        stdout = io.StringIO()
        args = ["--cuc", "/synthetic/cuc/tf/0.2.8", "--workbooks", "/synthetic/Workbooks"]
        if research:
            args.append("--research-multitoken")
        with (
            patch.object(audit, "load_pdf_directory", return_value=pdf) as load_pdf,
            patch.object(audit, "build_reviewed_cuc_index", return_value=index) as load_cuc,
            patch.object(audit, "ensure", side_effect=AssertionError("unexpected download")),
            patch.object(audit, "_write_private_report") as private_report,
            redirect_stdout(stdout),
        ):
            self.assertEqual(audit.main(args), 0)
            load_pdf.assert_called_once()
            load_cuc.assert_called_once()
            private_report.assert_not_called()
        return stdout.getvalue(), source, alignments

    def test_default_cli_payload_remains_identical_without_research_flag(self):
        output, source, alignments = self._run_cli(
            research=False,
            headword="secretlexeme privatelexeme hiddenlexeme",
            values=("secretlexeme", "privatelexemex", "hiddenlexeme"),
        )
        expected = json.dumps(
            audit.aggregate_alignment_stats(
                file_count=1, source=source, alignments=alignments,
            ),
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ) + "\n"
        self.assertEqual(output, expected)
        self.assertNotIn("multitoken_residual_research", output)

    def test_opt_in_exposes_existing_aggregate_without_private_text_or_report(self):
        output, source, _alignments = self._run_cli(
            research=True,
            headword="secretlexeme privatelexeme hiddenlexeme",
            values=("secretlexeme", "privatelexemex", "hiddenlexeme"),
        )
        data = json.loads(output)
        stats = data["multitoken_residual_research"]
        self.assertEqual(stats["occurrences"], 1)
        self.assertEqual(stats["classes"], {"one_missing_unique_containment": 1})
        self.assertEqual(stats["exact_hit_order"], {"in_order": 1})
        self.assertEqual(stats["one_missing_hypothesis_union"], {
            "occurrences": 1, "distinct_annotations": 1,
            "annotations_in_both_classes": 0,
        })
        self.assertEqual(stats["out_of_order_research"]["occurrences"], 0)
        for forbidden in (
            "secretlexeme", "privatelexeme", "hiddenlexeme", "privatelexemex",
            "KTU 1.14", "I.10", source.records[0].record_id,
            source.annotations[0].annotation_id,
        ):
            self.assertNotIn(forbidden, output)

    def test_opt_in_reports_reversed_exact_hits_without_lexical_realignment(self):
        output, _source, _alignments = self._run_cli(
            research=True, headword="a b c", values=("c", "bx", "a"),
        )
        stats = json.loads(output)["multitoken_residual_research"]
        self.assertEqual(stats["classes"], {"one_missing_unique_containment": 1})
        self.assertEqual(stats["exact_hit_order"], {"out_of_order": 1})
        self.assertEqual(stats["out_of_order_research"]["distinct_annotations"], 1)
        self.assertEqual(stats["one_missing_hypotheses"]["unique_containment"]["exact_hit_order"], {
            "out_of_order": 1,
        })


if __name__ == "__main__":
    unittest.main()
