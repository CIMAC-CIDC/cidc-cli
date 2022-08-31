from datetime import datetime
import pandas as pd
from _pytest.monkeypatch import MonkeyPatch
from unittest.mock import MagicMock

from cli.dbedit import list as dbedit_list
from .constants import (
    TEST_CLINICAL_URL_CSV,
    TEST_CLINICAL_URL_XLSX,
    TEST_METADATA_JSON,
    TEST_MISC_DATA_URL1,
    TEST_MISC_DATA_URL2,
    TEST_TRIAL_ID,
)


def test_list_clinical(monkeypatch):
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()
    begin.__enter__.return_value = session
    Session.begin.return_value = begin

    mock_trial = MagicMock()
    mock_trial.metadata_json = TEST_METADATA_JSON
    get_trial_if_exists = MagicMock()
    get_trial_if_exists.return_value = mock_trial

    file1, file2 = MagicMock(), MagicMock()
    file1.object_url = f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_XLSX}"
    file2.object_url = f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_CSV}"
    file1._created = datetime.fromisoformat("2020-01-01T12:34:45")
    file2._created = datetime.fromisoformat("2020-02-02T12:34:45")

    get_clinical_downloadable_files = MagicMock()
    get_clinical_downloadable_files.return_value = [file1, file2]

    mock_print = MagicMock()

    monkeypatch.setattr(dbedit_list, "Session", Session)
    monkeypatch.setattr(dbedit_list, "get_trial_if_exists", get_trial_if_exists)
    monkeypatch.setattr(
        dbedit_list, "get_clinical_downloadable_files", get_clinical_downloadable_files
    )
    monkeypatch.setattr("builtins.print", mock_print)

    dbedit_list.list_clinical(TEST_TRIAL_ID)

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    get_clinical_downloadable_files.assert_called_once_with(
        TEST_TRIAL_ID, session=session
    )
    begin.__exit__.assert_called_once()

    mock_print.assert_called_once()
    args, _ = mock_print.call_args
    assert len(args) == 1

    df = args[0]
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 5)
    assert all(
        col in df.columns
        for col in ["created", "filename", "num_participants", "object_url", "comment"]
    )

    assert df.equals(
        pd.DataFrame(
            [
                [
                    file1.object_url,
                    TEST_CLINICAL_URL_XLSX,
                    5,
                    file1._created,
                    "comment",
                ],
                [file2.object_url, TEST_CLINICAL_URL_CSV, 3, file2._created, pd.NA],
            ],
            columns=[
                "object_url",
                "filename",
                "num_participants",
                "created",
                "comment",
            ],
        )
    )


def test_list_misc_data(monkeypatch):
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()
    begin.__enter__.return_value = session
    Session.begin.return_value = begin

    mock_trial = MagicMock()
    mock_trial.metadata_json = TEST_METADATA_JSON
    get_trial_if_exists = MagicMock()
    get_trial_if_exists.return_value = mock_trial

    file1, file2 = MagicMock(), MagicMock()
    file1.object_url = f"{TEST_TRIAL_ID}/misc_data/{TEST_MISC_DATA_URL1}"
    file2.object_url = f"{TEST_TRIAL_ID}/misc_data/{TEST_MISC_DATA_URL2}"
    file1._created = datetime.fromisoformat("2020-01-01T12:34:45")
    file2._created = datetime.fromisoformat("2020-02-02T12:34:45")

    get_misc_data_files = MagicMock()
    get_misc_data_files.return_value = [file1, file2]

    mock_print = MagicMock()

    monkeypatch.setattr(dbedit_list, "Session", Session)
    monkeypatch.setattr(dbedit_list, "get_trial_if_exists", get_trial_if_exists)
    monkeypatch.setattr(dbedit_list, "get_misc_data_files", get_misc_data_files)
    monkeypatch.setattr("builtins.print", mock_print)

    dbedit_list.list_misc_data(TEST_TRIAL_ID)

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    get_misc_data_files.assert_called_once_with(TEST_TRIAL_ID, session=session)
    begin.__exit__.assert_called_once()

    mock_print.assert_called_once()
    args, _ = mock_print.call_args
    assert len(args) == 1

    df = args[0]
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 5)
    assert all(
        col in df.columns
        for col in ["batch_id", "created", "description", "filename", "object_url"]
    )

    assert df.equals(
        pd.DataFrame(
            [
                [
                    0,
                    file1.object_url,
                    TEST_MISC_DATA_URL1,
                    file1._created,
                    "description",
                ],
                [1, file2.object_url, TEST_MISC_DATA_URL2, file2._created, pd.NA],
            ],
            columns=["batch_id", "object_url", "filename", "created", "description"],
        )
    )


def test_list_shipments(monkeypatch):
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()
    begin.__enter__.return_value = session
    Session.begin.return_value = begin

    upload1, upload2 = MagicMock(), MagicMock()
    upload1.upload_type = "pbmc"
    upload2.upload_type = "plasma"
    upload1._created = datetime.fromisoformat("2020-01-01T12:34:45")
    upload2._created = datetime.fromisoformat("2020-02-02T12:34:45")

    upload1.metadata_patch = {
        "participants": [
            {"samples": [None] * 3},
            {"samples": [None]},
        ],
        "shipments": [{"manifest_id": "test_upload"}],
    }
    upload2.metadata_patch = {
        "participants": [
            {"samples": [None] * 3},
            {"samples": [None] * 2},
        ],
        "shipments": [{"manifest_id": "test_upload2"}],
    }

    get_shipments = MagicMock()
    get_shipments.return_value = [upload1, upload2]

    mock_print = MagicMock()
    monkeypatch.setattr(dbedit_list, "Session", Session)
    monkeypatch.setattr(dbedit_list, "get_shipments", get_shipments)
    monkeypatch.setattr("builtins.print", mock_print)

    dbedit_list.list_shipments(TEST_TRIAL_ID)

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    get_shipments.assert_called_once_with(TEST_TRIAL_ID, session=session)
    begin.__exit__.assert_called_once()

    mock_print.assert_called_once()
    args, _ = mock_print.call_args
    assert len(args) == 1

    df = args[0]
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 4)
    assert all(
        col in df.columns
        for col in ["created", "manifest_id", "num_samples", "upload_type"]
    )

    assert df.equals(
        pd.DataFrame(
            [
                [upload1.upload_type, "test_upload", 4, upload1._created],
                [upload2.upload_type, "test_upload2", 5, upload2._created],
            ],
            columns=["upload_type", "manifest_id", "num_samples", "created"],
        )
    )


class Test_list_data_cimac_ids:
    def setup(self):
        self.Session = MagicMock()
        self.session = MagicMock()
        self.begin = MagicMock()
        self.begin.__enter__.return_value = self.session
        self.Session.begin.return_value = self.begin

        self.mock_trial = MagicMock()
        self.mock_trial.metadata_json = TEST_METADATA_JSON

        self.get_trial_if_exists = MagicMock()
        self.get_trial_if_exists.return_value = self.mock_trial

        self.mock_list_clinical = MagicMock()
        self.mock_list_misc_data = MagicMock()

        self.real_print = print
        self.mock_print = MagicMock()

        self.monkeypatch = MonkeyPatch()
        self.monkeypatch.setattr(dbedit_list, "Session", self.Session)
        self.monkeypatch.setattr(
            dbedit_list, "get_trial_if_exists", self.get_trial_if_exists
        )
        self.monkeypatch.setattr(dbedit_list, "list_clinical", self.mock_list_clinical)
        self.monkeypatch.setattr(
            dbedit_list, "list_misc_data", self.mock_list_misc_data
        )
        self.monkeypatch.setattr("builtins.print", self.mock_print)

    def test_bail_outs(self):
        dbedit_list.list_data_cimac_ids(trial_id="foo", assay_or_analysis="bar")
        self.mock_print.assert_called_once_with(
            "Assay / analysis not supported:", "bar"
        )

        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="clinical_data"
        )
        self.mock_print.assert_not_called()
        self.mock_list_clinical.assert_called_once_with("foo")

        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(trial_id="foo", assay_or_analysis="misc_data")
        self.mock_print.assert_not_called()
        self.mock_list_misc_data.assert_called_once_with("foo")

    def _get_and_assert_df(self) -> pd.DataFrame:
        self.mock_print.assert_called_once()
        args, _ = self.mock_print.call_args
        assert len(args) == 1 and isinstance(args[0], pd.DataFrame)
        return args[0]

    def test_olink(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(trial_id="foo", assay_or_analysis="olink")
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "olink_batch",
                        "file": "combined",
                        "cimac_id": "CTTTPP101.00",
                    },
                    {
                        "batch_id": "olink_batch_2",
                        "file": f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_0/assay_npx.xlsx",
                        "cimac_id": "CTTTPP201.00",
                    },
                    {
                        "batch_id": "olink_batch_2",
                        "file": f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_1/assay_npx.xlsx",
                        "cimac_id": "CTTTPP102.00",
                    },
                ]
            )
        )

    def test_elisa(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(trial_id="foo", assay_or_analysis="elisa")
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {"assay_run_id": "elisa_batch", "cimac_id": "CTTTPP101.00"},
                    {"assay_run_id": "elisa_batch", "cimac_id": "CTTTPP201.00"},
                    {"assay_run_id": "elisa_batch_2", "cimac_id": "CTTTPP102.00"},
                ]
            )
        )

    def test_nanostring(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(trial_id="foo", assay_or_analysis="nanostring")
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "nanostring_batch",
                        "run_id": "nanostring_batch_run",
                        "cimac_id": "CTTTPP101.00",
                    },
                    {
                        "batch_id": "nanostring_batch",
                        "run_id": "nanostring_batch_run_2",
                        "cimac_id": "CTTTPP201.00",
                    },
                    {
                        "batch_id": "nanostring_batch_2",
                        "run_id": "nanostring_batch_2_run",
                        "cimac_id": "CTTTPP102.00",
                    },
                ]
            )
        )

    def test_rna_level1_analysis(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="rna_level1_analysis"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {"cimac_id": cimac_id}
                    for cimac_id in ["CTTTPP101.00", "CTTTPP201.00", "CTTTPP102.00"]
                ]
            )
        )

    def test_wes_analysis(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="wes_analysis"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "run_id": "CTTTPP101.00",
                        "tumor_cimac_id": "CTTTPP101.00",
                        "normal_cimac_id": "CTTTPP10N.00",
                    },
                    {
                        "run_id": "CTTTPP102.00",
                        "tumor_cimac_id": "CTTTPP102.00",
                        "normal_cimac_id": "CTTTPP10N.00",
                    },
                    {
                        "run_id": "CTTTPP201.00",
                        "tumor_cimac_id": "CTTTPP201.00",
                        "normal_cimac_id": "CTTTPP20N.00",
                    },
                    {
                        "run_id": "CTTTPP201.00",
                        "tumor_cimac_id": "CTTTPP201.00",
                        "normal_cimac_id": "CTTTPP20N.00",
                    },
                    {
                        "run_id": "CTTTPP102.00",
                        "tumor_cimac_id": "CTTTPP102.00",
                        "normal_cimac_id": "CTTTPP10N.00",
                    },
                ]
            )
        )

    def test_wes_analysis_old(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="wes_analysis_old"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "run_id": "CTTTPP201.00",
                        "tumor_cimac_id": "CTTTPP201.00",
                        "normal_cimac_id": "CTTTPP20N.00",
                    },
                    {
                        "run_id": "CTTTPP102.00",
                        "tumor_cimac_id": "CTTTPP102.00",
                        "normal_cimac_id": "CTTTPP10N.00",
                    },
                ]
            )
        )

    def test_wes_tumor_only_analysis(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="wes_tumor_only_analysis"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {"cimac_id": cimac_id}
                    for cimac_id in [
                        "CTTTPP101.00",
                        "CTTTPP102.00",
                        "CTTTPP201.00",
                        "CTTTPP201.00",
                        "CTTTPP102.00",
                    ]
                ]
            )
        )

    def test_wes_tumor_only_analysis_old(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="wes_tumor_only_analysis_old"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame([{"cimac_id": "CTTTPP201.00"}, {"cimac_id": "CTTTPP102.00"}])
        )

    def test_microbiome_analysis(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="microbiome_analysis"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "microbiome_batch",
                    },
                    {
                        "batch_id": "microbiome_batch_2",
                    },
                ]
            )
        )

    def test_cytof_analysis(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="cytof_analysis"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "cytof_batch",
                        "cimac_id": "CTTTPP101.00",
                    },
                    {
                        "batch_id": "cytof_batch",
                        "cimac_id": "CTTTPP201.00",
                    },
                    {
                        "batch_id": "cytof_batch_2",
                        "cimac_id": "CTTTPP102.00",
                    },
                ]
            )
        )

    def test_batched_analysis(self):
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="ctdna_analysis"
        )
        df: pd.DataFrame = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "ctdna_analysis_batch",
                        "cimac_id": "CTTTPP101.00",
                    },
                    {
                        "batch_id": "ctdna_analysis_batch",
                        "cimac_id": "CTTTPP201.00",
                    },
                    {
                        "batch_id": "ctdna_analysis_batch_2",
                        "cimac_id": "CTTTPP102.00",
                    },
                ]
            )
        )

    def test_generic_assay_with_ids(self):
        self.mock_print.reset_mock()
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(
            trial_id="foo", assay_or_analysis="atacseq_analysis"
        )

        df: pd.Series = self._get_and_assert_df()

        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "atacseq_analysis_batch",
                        "cimac_id": "CTTTPP101.00",
                    },
                    {
                        "batch_id": "atacseq_analysis_batch",
                        "cimac_id": "CTTTPP201.00",
                    },
                    {
                        "batch_id": "atacseq_analysis_batch_2",
                        "cimac_id": "CTTTPP102.00",
                    },
                ]
            )
        )

    def test_generic_assay_no_ids(self):
        self.mock_print.reset_mock()
        self.mock_print.reset_mock()
        dbedit_list.list_data_cimac_ids(trial_id="foo", assay_or_analysis="wes")

        df: pd.Series = self._get_and_assert_df()
        assert df.equals(
            pd.DataFrame(
                [
                    {
                        "batch_id": "0",
                        "cimac_id": "CTTTPP101.00",
                    },
                    {
                        "batch_id": "0",
                        "cimac_id": "CTTTPP201.00",
                    },
                    {
                        "batch_id": "1",
                        "cimac_id": "CTTTPP102.00",
                    },
                ]
            )
        )
