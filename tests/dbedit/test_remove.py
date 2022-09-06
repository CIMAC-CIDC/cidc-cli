from copy import deepcopy
from datetime import datetime
from deepdiff import DeepDiff
import pytest
from _pytest.monkeypatch import MonkeyPatch
from typing import Dict, List
from unittest.mock import MagicMock, call

from cli.dbedit import remove as dbedit_remove
from .constants import (
    TEST_CLINICAL_URL_CSV,
    TEST_CLINICAL_URL_XLSX,
    TEST_MANIFEST_ID,
    TEST_METADATA_JSON,
    TEST_TRIAL_ID,
)

CLIPPED_METADATA_SHIPMENTS: dict = {
    "analysis": TEST_METADATA_JSON["analysis"],
    "assays": TEST_METADATA_JSON["assays"],
    "clinical_data": TEST_METADATA_JSON["clinical_data"],
    "participants": [
        {
            "cimac_participant_id": "CTTTPP1",
            "samples": [
                {"cimac_id": "CTTTPP102.00"},
            ],
        },
        {
            "cimac_participant_id": "CTTTPP3",
            "samples": [
                {"cimac_id": "CTTTPP301.00"},
                {"cimac_id": "CTTTPP303.00"},
            ],
        },
    ],
    "shipments": [
        {"manifest_id": TEST_MANIFEST_ID + "2"},
    ],
}
CLIPPED_METADATA_TARGET_CLINICAL: dict = {
    "analysis": TEST_METADATA_JSON["analysis"],
    "assays": TEST_METADATA_JSON["assays"],
    "clinical_data": {
        "records": [
            {
                "clinical_file": {
                    "object_url": f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_CSV}",
                    "number_of_participants": 3,
                },
            },
        ],
    },
    "participants": TEST_METADATA_JSON["participants"],
    "shipments": TEST_METADATA_JSON["shipments"],
}
CLIPPED_METADATA_ALL_CLINICAL: dict = {
    "analysis": TEST_METADATA_JSON["analysis"],
    "assays": TEST_METADATA_JSON["assays"],
    "participants": TEST_METADATA_JSON["participants"],
    "shipments": TEST_METADATA_JSON["shipments"],
}


def test_remove_clinical(monkeypatch):
    # mock the class
    DownloadableFiles = MagicMock()
    monkeypatch.setattr(dbedit_remove, "DownloadableFiles", DownloadableFiles)

    # mock the session itself
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()

    # mock downlodable files
    mock_files = [MagicMock(), MagicMock()]
    mock_files[0].object_url = f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_XLSX}"
    mock_files[1].object_url = f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_CSV}"

    # mock query for individual file
    query = MagicMock()
    filter_query = MagicMock()
    filter_query.all.return_value = [mock_files[0]]
    query.filter.return_value = filter_query

    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

    # mock getting all clinical files
    get_clinical_downloadable_files = MagicMock()
    get_clinical_downloadable_files.return_value = mock_files
    monkeypatch.setattr(
        dbedit_remove,
        "get_clinical_downloadable_files",
        get_clinical_downloadable_files,
    )

    # mock getting the trial
    get_trial_if_exists = MagicMock()
    mock_trial = MagicMock()
    mock_trial.metadata_json = deepcopy(TEST_METADATA_JSON)
    mock_trial._updated = datetime.fromisoformat("2020-01-01T12:34:45")
    get_trial_if_exists.return_value = mock_trial
    monkeypatch.setattr(dbedit_remove, "get_trial_if_exists", get_trial_if_exists)

    # mock table class
    TrialMetadata = MagicMock()
    monkeypatch.setattr(dbedit_remove, "TrialMetadata", TrialMetadata)

    # convenience function
    def reset_mocks():
        Session.reset_mock()
        session.reset_mock()
        begin.reset_mock()
        query.reset_mock()
        filter_query.reset_mock()
        get_clinical_downloadable_files.reset_mock()
        [mock.reset_mock() for mock in mock_files]
        get_trial_if_exists.reset_mock()
        mock_trial.reset_mock()

    # test for proper removal of single file
    reset_mocks()
    dbedit_remove.remove_clinical(TEST_TRIAL_ID, TEST_CLINICAL_URL_XLSX)

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    begin.__exit__.assert_called_once()
    get_trial_if_exists.assert_called_once_with(
        TEST_TRIAL_ID, with_for_update=True, session=session
    )
    get_clinical_downloadable_files.assert_not_called()
    assert all(
        test_call in query.filter.call_args_list
        for test_call in [
            call(
                DownloadableFiles.trial_id == TEST_TRIAL_ID,
                DownloadableFiles.object_url
                == f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_XLSX}",
            ),
            call(
                TrialMetadata.trial_id == TEST_TRIAL_ID,
            ),
        ]
    )
    filter_query.all.assert_called_once_with()
    filter_query.update.assert_called_once()
    args, _ = filter_query.update.call_args
    assert len(args) == 1

    assert isinstance(args[0][TrialMetadata._updated], datetime)
    assert args[0][TrialMetadata._updated] != datetime.fromisoformat(
        "2020-01-01T12:34:45"
    )
    assert (
        DeepDiff(args[0][TrialMetadata.metadata_json], CLIPPED_METADATA_TARGET_CLINICAL)
        == {}
    )

    session.delete.assert_called_once_with(mock_files[0])

    # test for proper removal of all files
    reset_mocks()
    dbedit_remove.remove_clinical(TEST_TRIAL_ID, "*")

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    begin.__exit__.assert_called_once()
    get_trial_if_exists.assert_called_once_with(
        TEST_TRIAL_ID,
        with_for_update=True,
        session=session,
    )
    get_clinical_downloadable_files.assert_called_once_with(
        TEST_TRIAL_ID,
        session=session,
    )

    filter_query.update.assert_called_once()
    args, _ = filter_query.update.call_args
    assert len(args) == 1
    assert isinstance(args[0][TrialMetadata._updated], datetime)

    assert args[0][TrialMetadata._updated] != datetime.fromisoformat(
        "2020-01-01T12:34:45"
    )
    assert (
        DeepDiff(args[0][TrialMetadata.metadata_json], CLIPPED_METADATA_ALL_CLINICAL)
        == {}
    )

    assert session.delete.call_count == 2
    session.delete.assert_has_calls(
        [
            call(mock_files[0]),
            call(mock_files[1]),
        ]
    )

    # check that it exits if no matching file found
    reset_mocks()
    filter_query.all.return_value = []
    query.filter.return_value = filter_query
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_clinical(
            trial_id=TEST_TRIAL_ID,
            target_id=TEST_CLINICAL_URL_XLSX,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    session.add.assert_not_called()
    session.delete.assert_not_called()

    # check that it exits if no files found for *
    reset_mocks()
    get_clinical_downloadable_files.return_value = []
    monkeypatch.setattr(
        dbedit_remove,
        "get_clinical_downloadable_files",
        get_clinical_downloadable_files,
    )

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_clinical(
            trial_id=TEST_TRIAL_ID,
            target_id="*",
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    session.add.assert_not_called()
    session.delete.assert_not_called()


def test_remove_samples_from_blob():
    samples_to_remove: Dict[str, List[str]] = {
        "CTTTPP1": ["CTTTPP101.00"],
        "CTTTPP2": ["CTTTPP201.00", "CTTTPP202.00"],
        "CTTTPP3": ["CTTTPP302.00"],
    }

    res = dbedit_remove._remove_samples_from_blob(
        metadata_json=TEST_METADATA_JSON,
        samples_to_remove=samples_to_remove,
    )

    # this doesn't remove the shipment itself
    clip_just_samples = deepcopy(CLIPPED_METADATA_SHIPMENTS)
    clip_just_samples["shipments"] = TEST_METADATA_JSON["shipments"]
    assert res == clip_just_samples


def test_remove_shipment(monkeypatch):
    # mock the session itself
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()
    query = MagicMock()
    filter_query = MagicMock()

    query.filter.return_value = filter_query
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

    # mock getting the trial
    get_trial_if_exists = MagicMock()
    mock_trial = MagicMock()
    mock_trial.metadata_json = TEST_METADATA_JSON
    mock_trial._updated = datetime.fromisoformat("2020-01-01T12:34:45")
    get_trial_if_exists.first.return_value = mock_trial
    monkeypatch.setattr(dbedit_remove, "get_trial_if_exists", get_trial_if_exists)

    # mock getting the uploads
    mock_uploads = [MagicMock(), MagicMock(), MagicMock()]
    mock_uploads[0].metadata_patch = {
        "participants": [
            {
                "cimac_participant_id": "CTTTPP1",
                "samples": [
                    {"cimac_id": "CTTTPP101.00"},
                ],
            },
        ],
        "shipments": [{"manifest_id": TEST_MANIFEST_ID}],
    }  # TARGET: should be returned
    mock_uploads[1].metadata_patch = {
        "participants": [
            {
                "cimac_participant_id": "CTTTPP1",
                "samples": [
                    {"cimac_id": "CTTTPP102.00"},
                ],
            },
            {
                "cimac_participant_id": "CTTTPP3",
                "samples": [
                    {"cimac_id": "CTTTPP302.00"},
                ],
            },
        ],
        "shipments": [{"manifest_id": TEST_MANIFEST_ID + "2"}],
    }  # should be returned

    mock_uploads[2].metadata_patch = {
        "participants": [
            {
                "cimac_participant_id": "CTTTPP2",
                "samples": [
                    {"cimac_id": "CTTTPP201.00"},
                    {"cimac_id": "CTTTPP202.00"},
                ],
            },
            {
                "cimac_participant_id": "CTTTPP3",
                "samples": [
                    {"cimac_id": "CTTTPP301.00"},
                    {"cimac_id": "CTTTPP303.00"},
                ],
            },
        ],
        "shipments": [{"manifest_id": TEST_MANIFEST_ID}],
    }
    get_shipments = MagicMock()
    get_shipments.return_value = mock_uploads
    monkeypatch.setattr(dbedit_remove, "get_shipments", get_shipments)

    # mock table class
    TrialMetadata = MagicMock()
    monkeypatch.setattr(dbedit_remove, "TrialMetadata", TrialMetadata)

    # convenience function
    def reset_mocks():
        Session.reset_mock()
        session.reset_mock()
        begin.reset_mock()
        get_trial_if_exists.reset_mock()
        mock_trial.reset_mock()
        [mock.reset_mock() for mock in mock_uploads]
        get_shipments.reset_mock()

    # test for proper removal
    reset_mocks()
    dbedit_remove.remove_shipment(
        trial_id=TEST_TRIAL_ID,
        target_id=TEST_MANIFEST_ID,
    )

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    begin.__exit__.assert_called_once()
    get_trial_if_exists.assert_called_once_with(
        TEST_TRIAL_ID, with_for_update=True, session=session
    )
    get_shipments.assert_called_once_with(TEST_TRIAL_ID, session=session)

    args, _ = filter_query.update.call_args
    assert len(args) == 1

    assert isinstance(args[0][TrialMetadata._updated], datetime)
    assert args[0][TrialMetadata._updated] != datetime.fromisoformat(
        "2020-01-01T12:34:45"
    )
    args[0][TrialMetadata.metadata_json] == CLIPPED_METADATA_SHIPMENTS

    assert session.delete.call_count == 2
    session.delete.assert_has_calls(
        [
            call(mock_uploads[0]),
            call(mock_uploads[2]),
        ]
    )

    # check that it exits if no samples are in the matching manifest
    reset_mocks()
    remove_samples_from_blob = MagicMock()
    monkeypatch.setattr(
        dbedit_remove, "_remove_samples_from_blob", remove_samples_from_blob
    )

    empty_shipment = MagicMock()
    empty_shipment.metadata_json = {
        "participants": [],
        "shipments": [
            {"manifest_id": TEST_MANIFEST_ID},
        ],
    }
    get_shipments.return_value = [empty_shipment]
    monkeypatch.setattr(dbedit_remove, "get_shipments", get_shipments)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_shipment(
            trial_id=TEST_TRIAL_ID,
            target_id=TEST_MANIFEST_ID,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    remove_samples_from_blob.assert_not_called()
    session.add.assert_not_called()
    session.delete.assert_not_called()

    # check that it exits if no matching manifest found
    reset_mocks()
    remove_samples_from_blob.reset_mock()
    get_shipments.return_value = []
    monkeypatch.setattr(dbedit_remove, "get_shipments", get_shipments)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_shipment(
            trial_id=TEST_TRIAL_ID,
            target_id=TEST_MANIFEST_ID,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    remove_samples_from_blob.assert_not_called()
    session.add.assert_not_called()
    session.delete.assert_not_called()


class Test_remove_data:
    def teardown(self):
        self.monkeypatch.setattr("builtins.print", self.real_print)

    def setup(self):
        self.Session = MagicMock()
        self.begin = MagicMock()
        self.session = MagicMock()
        self.query = MagicMock()
        self.filter_query = MagicMock()

        self.query.filter.return_value = self.filter_query
        self.session.query.return_value = self.query
        self.begin.__enter__.return_value = self.session
        self.Session.begin.return_value = self.begin

        self.mock_trial = MagicMock()
        self.mock_trial.metadata_json = deepcopy(TEST_METADATA_JSON)

        self.get_trial_if_exists = MagicMock()
        self.get_trial_if_exists.return_value = self.mock_trial

        self.mock_remove_clinical = MagicMock()
        self.mock_remove_misc_data = MagicMock()

        self.real_print = print
        self.mock_print = MagicMock()

        self.DownloadableFiles = MagicMock()
        self.TrialMetadata = MagicMock()

        self.monkeypatch = MonkeyPatch()
        self.monkeypatch.setattr(dbedit_remove, "Session", self.Session)
        self.monkeypatch.setattr(
            dbedit_remove, "get_trial_if_exists", self.get_trial_if_exists
        )
        self.monkeypatch.setattr(
            dbedit_remove, "remove_clinical", self.mock_remove_clinical
        )
        self.monkeypatch.setattr(
            dbedit_remove, "DownloadableFiles", self.DownloadableFiles
        )
        self.monkeypatch.setattr(dbedit_remove, "TrialMetadata", self.TrialMetadata)
        self.monkeypatch.setattr("builtins.print", self.mock_print)

    def test_bail_outs(self):
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="bar", target_id=tuple()
        )
        self.mock_print.assert_called_once_with(
            "Assay / analysis not supported:", "bar"
        )

        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="clinical_data", target_id=("bar",)
        )
        self.mock_print.assert_not_called()
        self.mock_remove_clinical.assert_called_once_with(
            trial_id="foo", target_id="bar"
        )

    def test_olink(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="olink", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find olink batch bar for trial foo"
        )
        self.query.assert_not_called()

        # if no combined file, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=("olink_batch_2", "combined"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find a combined file for olink batch olink_batch_2 for trial foo"
        )
        self.query.assert_not_called()

        # if no matching file, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=("olink_batch_2", "bar"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find a file bar in olink batch olink_batch_2 for trial foo"
        )
        self.query.assert_not_called()

        # remove a single file
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["assays"]["olink"]["batches"][1]["records"].pop(0)
        self.mock_print.reset_mock()
        target_id = (
            "olink_batch_2",
            f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_0/assay_npx.xlsx",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing olink values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_0/assay_npx.xlsx",
            ]
        )

        # remove a combined file
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"]["olink"]["batches"][0].pop("combined")
        self.mock_print.reset_mock()
        target_id = (
            "olink_batch",
            "combined",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing olink values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/olink/batch_olink_batch/combined_npx.xlsx",
            ]
        )

        # remove a whole batch
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"]["olink"]["batches"].pop(1)
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=("olink_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing olink values {('olink_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_1/assay_npx.xlsx",
            ]
        )

        # remove a study-wide file
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"]["olink"].pop("study")
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=("study",),
        )

        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing olink values {('study',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/olink/study_npx.xlsx",
                f"{TEST_TRIAL_ID}/olink/ALL object_urls",
            ]
        )

        # remove last record removes whole batch and assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"].pop("olink")
        self.mock_print.reset_mock()
        target_id = (
            "olink_batch",
            f"{TEST_TRIAL_ID}/olink/batch_olink_batch/chip_0/assay_npx.xlsx",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="olink",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing olink values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/olink/batch_olink_batch/chip_0/assay_npx.xlsx",
                f"{TEST_TRIAL_ID}/olink/batch_olink_batch/chip_0/ALL object_urls",
                f"{TEST_TRIAL_ID}/olink/batch_olink_batch/ALL object_urls",
                f"{TEST_TRIAL_ID}/olink/ALL object_urls",
            ]
        )

    def test_elisa(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="elisa", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find elisa batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single run
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["assays"]["elisa"].pop(0)
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="elisa",
            target_id=("elisa_batch",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing elisa values {('elisa_batch',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/elisa/elisa_batch/assay.xlsx",
            ]
        )

        # remove last run removes whole assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"].pop("elisa")
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="elisa",
            target_id=("elisa_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing elisa values {('elisa_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/elisa/elisa_batch_2/assay.xlsx",
                f"{TEST_TRIAL_ID}/elisa/elisa_batch_2/ALL object_urls",
            ]
        )

    def test_nanostring(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="nanostring", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find nanostring batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # if no matching run_id, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="nanostring",
            target_id=("nanostring_batch", "bar"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find a run bar in nanostring batch nanostring_batch for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single run
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["assays"]["nanostring"][0]["runs"].pop(0)
        self.mock_print.reset_mock()
        target_id = (
            "nanostring_batch",
            "nanostring_batch_run",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="nanostring",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing nanostring values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run/control.rcc",
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run/CTTTPP101.00.rcc",
            ]
        )

        # remove a single batch
        target_metadata["assays"]["nanostring"].pop(1)
        self.mock_print.reset_mock()
        self.DownloadableFiles.object_url.reset_mock()
        self.filter_query.update.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="nanostring",
            target_id=("nanostring_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing nanostring values {('nanostring_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch_2/normalized_data.csv",
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch_2/nanostring_batch_2_run/control.rcc",
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch_2/nanostring_batch_2_run/CTTTPP102.00.rcc",
            ]
        )
        # remove last run removes whole batch and assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"].pop("nanostring")
        self.mock_print.reset_mock()
        target_id = ("nanostring_batch", "nanostring_batch_run_2")
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="nanostring",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing nanostring values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run_2/control.rcc",
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run_2/CTTTPP201.00.rcc",
                f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/normalized_data.csv",
            ]
        )

    def test_cytof_analysis(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="cytof_analysis", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find cytof analysis batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # if no matching run_id, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="cytof_analysis",
            target_id=("cytof_batch", "bar"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find cytof analysis for sample bar in batch cytof_batch for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single run
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["assays"]["cytof"][0]["records"][0].pop("output_files")
        self.mock_print.reset_mock()
        target_id = (
            "cytof_batch",
            "CTTTPP101.00",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="cytof_analysis",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing cytof_analysis values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/CTTTPP101.00/assignment.csv",
                f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/CTTTPP101.00/source.fcs",
            ]
        )

        # remove a single batch
        target_metadata["assays"]["cytof"][1].pop("astrolabe_analysis")
        target_metadata["assays"]["cytof"][1]["records"][0].pop("output_files")
        self.mock_print.reset_mock()
        self.DownloadableFiles.object_url.reset_mock()
        self.filter_query.update.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="cytof_analysis",
            target_id=("cytof_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing cytof_analysis values {('cytof_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch_2/reports.zip",
                f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch_2/CTTTPP102.00/assignment.csv",
                f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch_2/CTTTPP102.00/source.fcs",
            ]
        )

    def test_microbiome_analysis(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="microbiome_analysis", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find microbiome analysis batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single batch
        self.mock_print.reset_mock()
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["analysis"]["microbiome_analysis"]["batches"].pop(0)
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="microbiome_analysis",
            target_id=("microbiome_batch",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing microbiome_analysis values {('microbiome_batch',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/microbiome_analysis/microbiome_batch/summary.pdf",
            ],
        )

        # remove last batch removes whole assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        self.mock_print.reset_mock()
        target_metadata["analysis"].pop("microbiome_analysis")
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="microbiome_analysis",
            target_id=("microbiome_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing microbiome_analysis values {('microbiome_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/microbiome_analysis/microbiome_batch_2/summary.pdf",
            ],
        )

    def test_rna_level1_analysis(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="rna_level1_analysis", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find RNA analysis for bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single sample
        self.mock_print.reset_mock()
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["analysis"]["rna_analysis"]["level_1"].pop(0)
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="rna_level1_analysis",
            target_id=("CTTTPP101.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing rna_level1_analysis values {('CTTTPP101.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/rna/CTTTPP101.00/analysis/error.yaml",
            ],
        )

        # remove down to a single samples
        self.mock_print.reset_mock()
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["analysis"]["rna_analysis"]["level_1"].pop(
            1
        )  # the last of 3 (now 2)
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="rna_level1_analysis",
            target_id=("CTTTPP102.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing rna_level1_analysis values {('CTTTPP102.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/rna/CTTTPP102.00/analysis/error.yaml",
            ],
        )

        # remove last sample removes whole assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        self.mock_print.reset_mock()
        target_metadata["analysis"].pop("rna_analysis")
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="rna_level1_analysis",
            target_id=("CTTTPP201.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing rna_level1_analysis values {('CTTTPP201.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/rna/CTTTPP201.00/analysis/error.yaml",
            ],
        )

    def test_wes_analysis(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="wes_analysis", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find WES paired analysis for bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single pair run
        self.mock_print.reset_mock()
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["analysis"]["wes_analysis"]["pair_runs"].pop(0)
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_analysis",
            target_id=("CTTTPP101.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes_analysis values {('CTTTPP101.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes/CTTTPP101.00/analysis/error.yaml",
            ],
        )

        # remove a pair run in both "wes_analysis" and "wes_analysis_old"
        self.mock_print.reset_mock()
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["analysis"]["wes_analysis"]["pair_runs"].pop(
            0
        )  # the second of 3, now first 2
        target_metadata["analysis"]["wes_analysis_old"]["pair_runs"].pop(1)
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_analysis",
            target_id=("CTTTPP102.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes_analysis values {('CTTTPP102.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes/CTTTPP102.00/analysis/error.yaml",
                f"{TEST_TRIAL_ID}/wes/CTTTPP102.00/analysis/error.yaml",
            ],
        )

        # old_only, there's another one in wes_analysis
        # remove last pair run removes whole assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        self.mock_print.reset_mock()
        target_metadata["analysis"].pop("wes_analysis_old")
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_analysis_old",
            target_id=("CTTTPP201.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes_analysis_old values {('CTTTPP201.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes/CTTTPP201.00/analysis/error.yaml",
            ],
        )

    def test_wes_tumor_only_analysis(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_tumor_only_analysis",
            target_id=("bar",),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find WES tumor-only analysis for bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single pair run
        self.mock_print.reset_mock()
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["analysis"]["wes_tumor_only_analysis"]["runs"].pop(0)
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_tumor_only_analysis",
            target_id=("CTTTPP101.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes_tumor_only_analysis values {('CTTTPP101.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP101.00/analysis/error.yaml",
            ],
        )

        # remove a pair run in both "wes_tumor_only_analysis" and "wes_tumor_only_analysis_old"
        self.mock_print.reset_mock()
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["analysis"]["wes_tumor_only_analysis"]["runs"].pop(
            0
        )  # the second of 3, now first 2
        target_metadata["analysis"]["wes_tumor_only_analysis_old"]["runs"].pop(1)
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_tumor_only_analysis",
            target_id=("CTTTPP102.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes_tumor_only_analysis values {('CTTTPP102.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP102.00/analysis/error.yaml",
                f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP102.00/analysis/error.yaml",
            ],
        )

        # old_only, there's another one in wes_tumor_only_analysis
        # remove last pair run removes whole assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        self.mock_print.reset_mock()
        target_metadata["analysis"].pop("wes_tumor_only_analysis_old")
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes_tumor_only_analysis_old",
            target_id=("CTTTPP201.00",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes_tumor_only_analysis_old values {('CTTTPP201.00',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP201.00/analysis/error.yaml",
            ],
        )

    def test_batched_analysis(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="ctdna_analysis", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find ctdna_analysis batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # if no matching cimac_id, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="ctdna_analysis",
            target_id=("ctdna_analysis_batch", "bar"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find ctdna_analysis for sample bar in batch ctdna_analysis_batch for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single batch
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["analysis"]["ctdna_analysis"]["batches"][0]["records"].pop(0)
        self.mock_print.reset_mock()
        target_id = (
            "ctdna_analysis_batch",
            "CTTTPP101.00",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="ctdna_analysis",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing ctdna_analysis values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/ctdna_analysis/ctdna_analysis_batch/CTTTPP101.00/genome-wide_plots.pdf",
            ]
        )

        # remove a single batch
        target_metadata["analysis"]["ctdna_analysis"]["batches"].pop(1)
        self.mock_print.reset_mock()
        self.DownloadableFiles.object_url.reset_mock()
        self.filter_query.update.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="ctdna_analysis",
            target_id=("ctdna_analysis_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing ctdna_analysis values {('ctdna_analysis_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/ctdna_analysis/ctdna_analysis_batch_2/summary_plots.pdf",
                f"{TEST_TRIAL_ID}/ctdna_analysis/ctdna_analysis_batch_2/CTTTPP102.00/genome-wide_plots.pdf",
            ]
        )
        # remove last run removes whole batch and assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["analysis"].pop("ctdna_analysis")
        self.mock_print.reset_mock()
        target_id = ("ctdna_analysis_batch", "CTTTPP201.00")
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="ctdna_analysis",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing ctdna_analysis values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/ctdna_analysis/ctdna_analysis_batch/CTTTPP201.00/genome-wide_plots.pdf",
                f"{TEST_TRIAL_ID}/ctdna_analysis/ctdna_analysis_batch/summary_plots.pdf",
            ]
        )

    def test_generic_assay_with_ids(self):
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="atacseq_analysis", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find atacseq_analysis batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # if no matching cimac_id, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="atacseq_analysis",
            target_id=("atacseq_analysis_batch", "bar"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find atacseq_analysis for sample bar in batch atacseq_analysis_batch for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single batch
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["analysis"]["atacseq_analysis"][0]["records"].pop(0)
        self.mock_print.reset_mock()
        target_id = (
            "atacseq_analysis_batch",
            "CTTTPP101.00",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="atacseq_analysis",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing atacseq_analysis values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/atacseq/CTTTPP101.00/analysis/aligned_sorted.bam",
            ]
        )

        # remove a single batch
        target_metadata["analysis"]["atacseq_analysis"].pop(1)
        self.mock_print.reset_mock()
        self.DownloadableFiles.object_url.reset_mock()
        self.filter_query.update.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="atacseq_analysis",
            target_id=("atacseq_analysis_batch_2",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing atacseq_analysis values {('atacseq_analysis_batch_2',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/atacseq/analysis/atacseq_analysis_batch_2/report.zip",
                f"{TEST_TRIAL_ID}/atacseq/CTTTPP102.00/analysis/aligned_sorted.bam",
            ]
        )

        # remove last run removes whole batch and assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["analysis"].pop("atacseq_analysis")
        self.mock_print.reset_mock()
        target_id = ("atacseq_analysis_batch", "CTTTPP201.00")
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="atacseq_analysis",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing atacseq_analysis values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/atacseq/CTTTPP201.00/analysis/aligned_sorted.bam",
                f"{TEST_TRIAL_ID}/atacseq/analysis/atacseq_analysis_batch/report.zip",
            ]
        )

    def test_generic_assay_no_ids(self):
        self.mock_print.reset_mock()
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="wes", target_id=("bar",)
        )
        # if no matching batch, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo", assay_or_analysis="wes", target_id=("bar",)
        )
        self.mock_print.assert_called_once_with(
            "Cannot find wes batch bar for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # if no matching cimac_id, bails
        self.mock_print.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes",
            target_id=("0", "bar"),
        )
        self.mock_print.assert_called_once_with(
            "Cannot find wes for sample bar in batch 0 for trial foo"
        )
        self.query.assert_not_called()
        self.session.delete.assert_not_called()

        # remove a single batch
        target_metadata = deepcopy(TEST_METADATA_JSON)
        target_metadata["assays"]["wes"][0]["records"].pop(0)
        self.mock_print.reset_mock()
        target_id = (
            "0",
            "CTTTPP101.00",
        )
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes/CTTTPP101.00/reads_0.bam",
                f"{TEST_TRIAL_ID}/wes/CTTTPP101.00/reads_1.bam",
            ]
        )

        # remove a single batch
        target_metadata["assays"]["wes"].pop(1)
        self.mock_print.reset_mock()
        self.DownloadableFiles.object_url.reset_mock()
        self.filter_query.update.reset_mock()
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes",
            target_id=("1",),
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes values {('1',)}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes/CTTTPP102.00/reads_0.bam",
            ]
        )
        # remove last run removes whole batch and assay
        self.filter_query.update.reset_mock()
        self.DownloadableFiles.object_url.in_.reset_mock()
        target_metadata["assays"].pop("wes")
        self.mock_print.reset_mock()
        target_id = ("0", "CTTTPP201.00")
        dbedit_remove.remove_data(
            trial_id="foo",
            assay_or_analysis="wes",
            target_id=target_id,
        )
        self.mock_print.assert_called_once_with(
            f"Updated trial foo, removing wes values {target_id}",
            f"along with {self.filter_query.delete()} files",
        )
        self.filter_query.update.assert_called_once()
        args, _ = self.filter_query.update.call_args
        assert (
            DeepDiff(args[0][self.TrialMetadata.metadata_json], target_metadata) == {}
        )
        self.DownloadableFiles.object_url.in_.assert_called_once_with(
            [
                f"{TEST_TRIAL_ID}/wes/CTTTPP201.00/reads_0.bam",
            ]
        )
