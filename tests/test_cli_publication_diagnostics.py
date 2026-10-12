"""Publication failures are CLI diagnostics, not hidden pipeline defects."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ugarit_context_parsing import cli


class PublicationCliDiagnosticsTests(unittest.TestCase):
    def _run(self, command: str, writer_name: str, *, writer_result=None, writer_error=None, construction_error=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"source"; source.mkdir()
            cuc=root/"cuc"; cuc.mkdir()
            output=root/"output"
            args=[command,str(source),"--input-format","csv","--cuc",str(cuc),"--output",str(output)]
            loaded=SimpleNamespace(root=source,files=("synthetic.csv",),records=())
            normalized=SimpleNamespace(records=(),annotations=())
            writer=unittest.mock.Mock(return_value=writer_result,side_effect=writer_error)
            build_name="build_feature_module" if command=="module" else "build_burns_module"
            report_name="build_feature_module_report" if command=="module" else "build_burns_module_report"
            with (
                patch.object(cli,"_load_source",return_value=loaded),
                patch.object(cli,"normalize_workbook_records",return_value=normalized),
                patch.object(cli,"build_reviewed_cuc_index",return_value=object()),
                patch.object(cli,"align_burns_source",return_value=()),
                patch.object(cli,build_name,return_value=object(),side_effect=construction_error),
                patch.object(cli,report_name,return_value=object()),
                patch.object(cli,writer_name,writer),
            ):
                return cli.main(args)

    def test_primary_writer_valueerror_is_concise(self):
        with self.assertRaisesRegex(SystemExit,"^module publication failed: synthetic unsafe output$"):
            self._run("module","write_feature_module",writer_error=ValueError("synthetic unsafe output"))

    def test_v1_writer_valueerror_is_concise(self):
        with self.assertRaisesRegex(SystemExit,"^legacy publication failed: synthetic unsafe output$"):
            self._run("module-v1","write_burns_module",writer_error=ValueError("synthetic unsafe output"))

    def test_primary_false_return_diagnostic_unchanged(self):
        with self.assertRaisesRegex(SystemExit,"^Text-Fabric refused the Burns feature-only module$"):
            self._run("module","write_feature_module",writer_result=False)

    def test_v1_false_return_diagnostic_unchanged(self):
        with self.assertRaisesRegex(SystemExit,"^Text-Fabric refused the generated Burns module$"):
            self._run("module-v1","write_burns_module",writer_result=False)

    def test_prepublication_construction_valueerror_is_not_swallowed(self):
        with self.assertRaisesRegex(ValueError,"synthetic programming bug"):
            self._run("module","write_feature_module",construction_error=ValueError("synthetic programming bug"))

    def test_success_paths_unchanged(self):
        self.assertEqual(self._run("module","write_feature_module",writer_result=True),0)
        self.assertEqual(self._run("module-v1","write_burns_module",writer_result=True),0)


if __name__=="__main__":
    unittest.main()
