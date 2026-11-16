"""Restricted #115 source-case review: synthetic fixtures, no Burns data in Git."""
from __future__ import annotations

import io
import json
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


class PrivateOneMissingReviewTests(unittest.TestCase):
    def _fixture(self):
        repeated = replace(_record(1, "a b c", 10), references="I.10, 20")
        records = (
            repeated,
            _record(2, "d e f", 30),
            _record(3, "g h", 40),       # exact lexical span
            _record(4, "i j", 50),       # reordered exact tokens; not one missing
            _record(5, "o p", 60),       # exact neighbor; exclude
            _record(6, "q r", 80),       # exact concatenation; exclude
            _record(7, "s t u", 90),     # zero overlap
            _record(8, "aa bb cc", 100), # multiple embeddings of bb
            _record(9, "w z v", 110),    # tied distance-1 local candidates
        )
        index = _index({
            10: ("a", "bx", "c"),
            20: ("c", "x", "a"),
            30: ("d", "ez", "f"),
            40: ("g", "h"),
            50: ("j", "i"),
            60: ("wrong",), 61: ("o", "p"),
            80: ("qr",),
            90: ("wrong", "other"),
            100: ("aa", "bbbb", "cc"),
            110: ("w", "y", "x", "v"),
        })
        source = normalize_workbook_records(records)
        return records, source, index, align_burns_source(source, index)

    def test_private_cases_match_source_safe_union_and_keep_only_unique_unconsumed_words(self):
        _records, source, index, alignments = self._fixture()
        result = audit.private_one_missing_review(
            source=source, alignments=alignments, index=index,
        )
        safe = audit.aggregate_multitoken_residual_research(
            source=source, alignments=alignments, index=index,
        )
        self.assertEqual(result["schema"], "burns-private-one-missing-v1")
        self.assertEqual(result["occurrences"], 3)
        self.assertEqual(result["distinct_annotations"], 2)
        self.assertEqual(result["occurrences"], safe["one_missing_hypothesis_union"]["occurrences"])
        self.assertEqual(result["distinct_annotations"], safe["one_missing_hypothesis_union"]["distinct_annotations"])
        self.assertEqual(result["class_occurrences"], {
            "unique_containment": 2, "unique_edit1": 1,
        })
        self.assertEqual(result["annotations_in_both_classes"], 1)
        self.assertEqual(result["class_distinct_annotations"], {
            "unique_containment": 2, "unique_edit1": 1,
        })
        cases = result["cases"]
        for kind in ("unique_containment", "unique_edit1"):
            class_cases = [case for case in cases if case["local_evidence"] == kind]
            independent_count = len({case["annotation_id"] for case in class_cases})
            self.assertEqual(independent_count, result["class_distinct_annotations"][kind])
            self.assertEqual(
                independent_count,
                safe["one_missing_hypotheses"][kind]["distinct_annotations"],
            )
        self.assertEqual([case["missing_token"] for case in cases], ["b", "b", "e"])
        self.assertEqual([case["cuc_candidate_g_cons"] for case in cases], ["bx", "x", "ez"])
        self.assertEqual([case["local_evidence"] for case in cases],
                         ["unique_containment", "unique_edit1", "unique_containment"])
        self.assertEqual([case["exact_hit_order"] for case in cases],
                         ["in_order", "out_of_order", "in_order"])
        self.assertEqual([case["presence_mask"] for case in cases], ["101"] * 3)
        self.assertEqual(cases[0]["burns_tokens"], ["a", "b", "c"])
        self.assertEqual(cases[0]["cuc_g_cons"], ["a", "bx", "c"])
        self.assertEqual(cases[0]["source_reference"], "I.10, 20")
        self.assertEqual(cases[0]["target"], {"tablet": "KTU 1.14", "column": "I", "line": 10})
        self.assertEqual(cases[0]["annotation_id"], cases[1]["annotation_id"])
        self.assertNotEqual(cases[0]["occurrence_id"], cases[1]["occurrence_id"])
        self.assertEqual([case["target"]["line"] for case in cases], [10, 20, 30])

    def test_cli_explicit_output_is_private_and_default_stdout_remains_aggregate_only(self):
        records, source, index, _alignments = self._fixture()
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "one-missing.json"
            out = io.StringIO()
            with (
                patch.object(audit, "load_pdf_directory",
                             return_value=SimpleNamespace(files=("synthetic.pdf",), records=records)),
                patch.object(audit, "build_reviewed_cuc_index", return_value=index),
                patch.object(audit, "ensure", side_effect=AssertionError("unexpected download")),
                redirect_stdout(out),
            ):
                self.assertEqual(audit.main([
                    "--workbooks", "/synthetic/Workbooks", "--cuc", "/synthetic/cuc",
                    "--research-multitoken", "--private-one-missing", str(private),
                ]), 0)
            result = json.loads(private.read_text(encoding="utf-8"))
            self.assertEqual(result["occurrences"], 3)
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o600)
            self.assertEqual(json.loads(out.getvalue())["multitoken_residual_research"]
                             ["one_missing_hypothesis_union"]["occurrences"], 3)
            for restricted in ("a b c", "KTU 1.14", "I.10, 20",
                               source.annotations[0].annotation_id, str(private)):
                self.assertNotIn(restricted, out.getvalue())

            with (
                patch.object(audit, "load_pdf_directory",
                             return_value=SimpleNamespace(files=("synthetic.pdf",), records=records)),
                patch.object(audit, "build_reviewed_cuc_index", return_value=index),
                patch.object(audit, "ensure", side_effect=AssertionError("unexpected download")),
                patch.object(audit, "_write_private_report") as writer,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(audit.main([
                    "--workbooks", "/synthetic/Workbooks", "--cuc", "/synthetic/cuc",
                ]), 0)
                writer.assert_not_called()

    def test_all_private_paths_collide_or_overlap_before_loading_any_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkout = root / "software"
            workbooks = root / "Workbooks"
            cuc = root / "cuc"
            outside = root / "private"
            for path in (checkout, workbooks, cuc, outside):
                path.mkdir()
            alias = root / "private-alias"
            alias.symlink_to(outside, target_is_directory=True)
            args = ["--workbooks", str(workbooks), "--cuc", str(cuc)]
            for options, reason in (
                (["--private-one-missing", str(checkout / "case.json")], "overlaps"),
                (["--private-one-missing", str(workbooks / "case.json")], "overlaps"),
                (["--private-one-missing", str(cuc / "otype.tf")], "overlaps"),
                (["--report", str(outside / "case.json"),
                  "--private-one-missing", str(alias / "case.json")], "same destination"),
                (["--private-out-of-order", str(outside / "case.json"),
                  "--private-one-missing", str(alias / "case.json")], "same destination"),
            ):
                with (
                    self.subTest(options=options),
                    patch.object(audit, "ROOT", checkout),
                    patch.object(audit, "load_pdf_directory",
                                 side_effect=AssertionError("source load before preflight")),
                    patch.object(audit, "build_reviewed_cuc_index",
                                 side_effect=AssertionError("index before preflight")),
                    patch.object(audit, "ensure",
                                 side_effect=AssertionError("download before preflight")),
                ):
                    with self.assertRaisesRegex(ValueError, reason):
                        audit.main([*args, *options])


if __name__ == "__main__":
    unittest.main()
