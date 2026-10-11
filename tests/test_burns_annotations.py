from __future__ import annotations

import csv
import tempfile
import unittest
import unicodedata
from dataclasses import fields
from pathlib import Path

from ugarit_context_parsing.annotations import (
    BurnsInterpretiveStatus,
    BurnsNormalizationError,
    BurnsSemanticStatus,
    BurnsTextualStatus,
    BurnsWorksheetRole,
    BurnsSourceRecord,
    normalize_workbook_records,
)
from ugarit_context_parsing.source import (
    WORKBOOK_FIELDS,
    WorkbookRecord,
    load_csv_directory,
)


WORKBOOK_I = "01 Workbook I - Divine Names (DNs)"
WORKBOOK_V = "05 Workbook V - Cultic Commodities"


def _record(**overrides: object) -> WorkbookRecord:
    values: dict[str, object] = {
        "source_file": f"{WORKBOOK_I}/Worksheet 1.csv",
        "source_row": 1,
        "source_page": 1,
        "section": "Section α",
        "root": "",
        "headword": "bʿl",
        "ktu": "1.14",
        "references": "I 1",
        "locus": "GP",
        "room": "1",
        "point": "3",
        "depth": "0.5",
        "disputed": "n",
        "comments": "synthetic annotation test",
    }
    values.update(overrides)
    return WorkbookRecord(**values)  # type: ignore[arg-type]


def _normalize(*records: WorkbookRecord):
    return normalize_workbook_records(records)


def _write_csv(path: Path, *, headword: str, ktu: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "source_page": 1,
        "section": "Section α",
        "root": "",
        "headword": headword,
        "ktu": ktu,
        "references": "I 1",
        "locus": "GP",
        "room": "1",
        "point": "",
        "depth": "",
        "disputed": "n",
        "comments": "synthetic loader-order control",
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WORKBOOK_FIELDS)
        writer.writeheader()
        writer.writerow(row)


class WorksheetIdentityTests(unittest.TestCase):
    def test_csv_and_pdf_paths_share_logical_identity_but_keep_raw_path(self):
        csv_record = _record(source_file=f"{WORKBOOK_I}/Worksheet 1.csv")
        pdf_record = _record(source_file=f"{WORKBOOK_I}/Worksheet 1.pdf")

        csv_source = _normalize(csv_record)
        pdf_source = _normalize(pdf_record)

        self.assertEqual(csv_source.records[0].worksheet_id, f"{WORKBOOK_I}/Worksheet 1")
        self.assertEqual(csv_source.records[0].worksheet_id, pdf_source.records[0].worksheet_id)
        self.assertEqual(csv_source.records[0].record_id, pdf_source.records[0].record_id)
        self.assertEqual(csv_source.annotations[0].annotation_id, pdf_source.annotations[0].annotation_id)
        self.assertEqual(csv_source.records[0].source_file, f"{WORKBOOK_I}/Worksheet 1.csv")
        self.assertEqual(pdf_source.records[0].source_file, f"{WORKBOOK_I}/Worksheet 1.pdf")

    def test_derives_workbook_and_all_five_worksheet_roles(self):
        expected = {
            1: BurnsWorksheetRole.PRIME_GP,
            2: BurnsWorksheetRole.PRIME_PH,
            3: BurnsWorksheetRole.DERIVED_COMMON,
            4: BurnsWorksheetRole.DERIVED_GP_ONLY,
            5: BurnsWorksheetRole.DERIVED_PH_ONLY,
        }
        for worksheet, role in expected.items():
            with self.subTest(worksheet=worksheet):
                result = _normalize(
                    _record(source_file=f"{WORKBOOK_V}/Worksheet {worksheet}.pdf")
                )
                row = result.records[0]
                self.assertEqual(row.workbook_number, 5)
                self.assertEqual(row.workbook_label, WORKBOOK_V)
                self.assertEqual(row.worksheet_number, worksheet)
                self.assertEqual(row.worksheet_role, role)

    def test_rejects_malformed_source_paths_instead_of_guessing(self):
        invalid = [
            "/absolute/Worksheet 1.csv",
            f"{WORKBOOK_I}/../Worksheet 1.csv",
            "Worksheet 1.csv",
            f"{WORKBOOK_I}/Worksheet 1.txt",
            "10 Workbook X - Synthetic/Worksheet 1.csv",
            f"{WORKBOOK_I}/Worksheet.csv",
            f"{WORKBOOK_I}/Worksheet 6.csv",
        ]
        for source_file in invalid:
            with self.subTest(source_file=source_file):
                with self.assertRaises(BurnsNormalizationError):
                    _normalize(_record(source_file=source_file))

    def test_rejects_invalid_row_or_page_from_direct_callers(self):
        for override in ({"source_row": 0}, {"source_page": 0}):
            with self.subTest(override=override):
                with self.assertRaises(BurnsNormalizationError):
                    _normalize(_record(**override))


class SourceRecordIdentityTests(unittest.TestCase):
    def test_preserves_every_workbook_record_field_losslessly(self):
        original = _record(
            source_page=7,
            source_row=9,
            section="Section β",
            root="qrb*†!?",
            headword="bʿl [x]",
            ktu="2.105",
            references="II 3–5",
            locus="PH",
            room="Court V (oven)",
            point="4a",
            depth="1.25",
            disputed="y",
            comments="line one\nline two; cf. note?",
        )
        normalized = _normalize(original).records[0]

        for name in (
            "source_file",
            "source_row",
            "source_page",
            "section",
            "root",
            "headword",
            "ktu",
            "references",
            "locus",
            "room",
            "point",
            "depth",
            "disputed",
            "comments",
        ):
            self.assertEqual(getattr(normalized, name), getattr(original, name), name)

    def test_record_id_is_full_sha256_and_changes_with_identity_fields(self):
        original = _normalize(_record()).records[0]
        self.assertRegex(original.record_id, r"^burns-record-sha256:[0-9a-f]{64}$")

        variants = [
            _record(source_row=2),
            _record(source_page=2),
            _record(source_file=f"{WORKBOOK_I}/Worksheet 2.csv"),
            _record(section="Section β"),
            _record(root="qrb"),
            _record(headword="mlk"),
            _record(ktu="1.15"),
            _record(references="II 2"),
            _record(locus="PH"),
            _record(room="2"),
            _record(point="4"),
            _record(depth="0.6"),
            _record(disputed="y"),
            _record(comments="changed"),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(
                    original.record_id,
                    _normalize(variant).records[0].record_id,
                )

    def test_nfc_is_used_for_identity_without_mutating_stored_source_text(self):
        nfc = "ṯ"
        nfd = unicodedata.normalize("NFD", nfc)
        self.assertNotEqual(nfc, nfd)

        a = _normalize(_record(headword=nfc)).records[0]
        b = _normalize(_record(headword=nfd)).records[0]

        self.assertEqual(a.record_id, b.record_id)
        self.assertEqual(a.headword, nfc)
        self.assertEqual(b.headword, nfd)

    def test_duplicate_logical_row_id_fails_closed(self):
        row = _record()
        with self.assertRaisesRegex(BurnsNormalizationError, r"(?i)duplicate.*record"):
            _normalize(row, row)

    def test_absolute_roots_and_filesystem_creation_order_do_not_change_ids(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            root_a = Path(tmp_a)
            root_b = Path(tmp_b)
            rel_1 = Path(WORKBOOK_I) / "Worksheet 1.csv"
            rel_2 = Path(WORKBOOK_I) / "Worksheet 2.csv"

            _write_csv(root_a / rel_2, headword="mlk", ktu="1.16")
            _write_csv(root_a / rel_1, headword="bʿl", ktu="1.14")
            _write_csv(root_b / rel_1, headword="bʿl", ktu="1.14")
            _write_csv(root_b / rel_2, headword="mlk", ktu="1.16")

            a = normalize_workbook_records(load_csv_directory(root_a).records)
            b = normalize_workbook_records(load_csv_directory(root_b).records)

        self.assertEqual([row.worksheet_id for row in a.records], [row.worksheet_id for row in b.records])
        self.assertEqual([row.record_id for row in a.records], [row.record_id for row in b.records])
        self.assertEqual(
            [annotation.annotation_id for annotation in a.annotations],
            [annotation.annotation_id for annotation in b.annotations],
        )


class SemanticAnnotationGroupingTests(unittest.TestCase):
    def test_adjacent_findspot_subrows_form_one_annotation_without_losing_rows(self):
        first = _record(comments="first", locus="GP", room="1")
        second = _record(
            source_row=2,
            source_page=2,
            comments="second",
            locus="PH",
            room="2",
        )

        result = _normalize(first, second)

        self.assertEqual(len(result.records), 2)
        self.assertEqual(len(result.annotations), 1)
        annotation = result.annotations[0]
        self.assertEqual(annotation.record_ids, tuple(row.record_id for row in result.records))
        self.assertEqual(annotation.first_source_row, 1)
        self.assertEqual(result.records[0].comments, "first")
        self.assertEqual(result.records[1].comments, "second")
        self.assertEqual(result.records[0].locus, "GP")
        self.assertEqual(result.records[1].locus, "PH")
        self.assertRegex(annotation.annotation_id, r"^burns-annotation-sha256:[0-9a-f]{64}$")

    def test_noncontiguous_identical_textual_keys_remain_distinct_annotations(self):
        first_a = _record(source_row=1, headword="bʿl", ktu="1.14", references="I 1")
        middle_b = _record(source_row=2, headword="mlk", ktu="1.16", references="II 2")
        later_a = _record(source_row=3, headword="bʿl", ktu="1.14", references="I 1")

        result = _normalize(first_a, middle_b, later_a)

        self.assertEqual(len(result.annotations), 3)
        self.assertNotEqual(result.annotations[0].annotation_id, result.annotations[2].annotation_id)
        self.assertEqual(result.annotations[0].headword, result.annotations[2].headword)
        self.assertEqual(result.annotations[0].first_source_row, 1)
        self.assertEqual(result.annotations[2].first_source_row, 3)

    def test_grouping_never_crosses_worksheet_boundary(self):
        a = _record(source_file=f"{WORKBOOK_I}/Worksheet 1.csv", source_row=1)
        b = _record(source_file=f"{WORKBOOK_I}/Worksheet 2.csv", source_row=1)

        result = _normalize(a, b)

        self.assertEqual(len(result.annotations), 2)
        self.assertNotEqual(result.annotations[0].worksheet_id, result.annotations[1].worksheet_id)

    def test_changed_shared_textual_field_starts_new_annotation(self):
        first = _record(source_row=1)
        second = _record(source_row=2, references="I 2")
        result = _normalize(first, second)
        self.assertEqual(len(result.annotations), 2)

    def test_member_findspot_change_changes_row_id_not_occurrence_id(self):
        first = _record(source_row=1)
        second_a = _record(source_row=2, locus="PH", comments="A")
        second_b = _record(source_row=2, locus="Acr", comments="B")

        a = _normalize(first, second_a)
        b = _normalize(first, second_b)

        self.assertEqual(a.annotations[0].annotation_id, b.annotations[0].annotation_id)
        self.assertNotEqual(a.records[1].record_id, b.records[1].record_id)

    def test_annotation_ids_are_adapter_neutral(self):
        csv_rows = (
            _record(source_file=f"{WORKBOOK_I}/Worksheet 1.csv", source_row=1),
            _record(source_file=f"{WORKBOOK_I}/Worksheet 1.csv", source_row=2, locus="PH"),
        )
        pdf_rows = tuple(
            WorkbookRecord(**{**row.__dict__, "source_file": f"{WORKBOOK_I}/Worksheet 1.pdf"})
            for row in csv_rows
        )

        csv_source = _normalize(*csv_rows)
        pdf_source = _normalize(*pdf_rows)

        self.assertEqual(
            [row.record_id for row in csv_source.records],
            [row.record_id for row in pdf_source.records],
        )
        self.assertEqual(
            [annotation.annotation_id for annotation in csv_source.annotations],
            [annotation.annotation_id for annotation in pdf_source.annotations],
        )


class BurnsSemanticStatusTests(unittest.TestCase):
    def test_maps_fixed_workbook_sections_without_conflating_beta(self):
        alpha = _normalize(_record(section="Section α")).records[0]
        beta = _normalize(_record(section="Section β")).records[0]
        self.assertEqual(alpha.semantic_status, BurnsSemanticStatus.POSITIVE_FIXED)
        self.assertEqual(beta.semantic_status, BurnsSemanticStatus.HOMOGRAPH_EXCLUDED)

    def test_maps_contextual_workbook_sections_independently(self):
        path = f"{WORKBOOK_V}/Worksheet 1.csv"
        cases = {
            "Section α1": BurnsSemanticStatus.PROBABLE_CULTIC,
            "Section α2": BurnsSemanticStatus.NO_SECURE_CULTIC,
            "Section β": BurnsSemanticStatus.HOMOGRAPH_EXCLUDED,
        }
        for section, expected in cases.items():
            with self.subTest(section=section):
                row = _normalize(_record(source_file=path, section=section)).records[0]
                self.assertEqual(row.semantic_status, expected)

    def test_unsupported_section_combination_is_explicit_not_guessed(self):
        fixed_bad = _normalize(_record(section="Section α1")).records[0]
        contextual_bad = _normalize(
            _record(source_file=f"{WORKBOOK_V}/Worksheet 1.csv", section="Section α")
        ).records[0]
        self.assertEqual(fixed_bad.semantic_status, BurnsSemanticStatus.UNSUPPORTED)
        self.assertEqual(contextual_bad.semantic_status, BurnsSemanticStatus.UNSUPPORTED)

    def test_not_attested_is_non_textual_without_erasing_semantic_status(self):
        row = _normalize(
            _record(ktu="Not attested (synthetic note)", section="Section α")
        ).records[0]
        self.assertEqual(row.textual_status, BurnsTextualStatus.NON_TEXTUAL_NOT_ATTESTED)
        self.assertEqual(row.semantic_status, BurnsSemanticStatus.POSITIVE_FIXED)

    def test_normal_ktu_is_textual(self):
        row = _normalize(_record(ktu="1.14")).records[0]
        self.assertEqual(row.textual_status, BurnsTextualStatus.TEXTUAL)

    def test_uncertainty_like_comment_is_preserved_but_not_inferred(self):
        comment = "cf. another reading? perhaps uncertain"
        row = _normalize(_record(comments=comment)).records[0]
        self.assertEqual(row.comments, comment)
        self.assertEqual(row.interpretive_status, BurnsInterpretiveStatus.UNSPECIFIED)

    def test_worksheet_role_is_independent_from_semantic_status(self):
        row = _normalize(
            _record(
                source_file=f"{WORKBOOK_V}/Worksheet 5.pdf",
                section="Section α1",
            )
        ).records[0]
        self.assertEqual(row.worksheet_role, BurnsWorksheetRole.DERIVED_PH_ONLY)
        self.assertEqual(row.semantic_status, BurnsSemanticStatus.PROBABLE_CULTIC)


class ArchitectureIsolationTests(unittest.TestCase):
    def test_normalized_model_contains_no_cuc_or_alignment_fields(self):
        names = {field.name for field in fields(BurnsSourceRecord)}
        for forbidden in {"cuc_node", "cuc_nodes", "alignment", "targets", "column", "line"}:
            self.assertNotIn(forbidden, names)

    def test_normalization_does_not_mutate_inputs(self):
        record = _record()
        snapshot = record
        _normalize(record)
        self.assertEqual(record, snapshot)


if __name__ == "__main__":
    unittest.main()
