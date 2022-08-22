from copy import deepcopy
from datetime import datetime
import pytest
from typing import Dict, List
from unittest.mock import MagicMock, call

from cli.dbedit import remove as dbedit_remove

TEST_CLINICAL_FILE_URL: str = "clinical_file.xlsx"
TEST_MANIFEST_ID: str = "test_upload"
TEST_TRIAL_ID: str = "test_prism_trial_id"

TRIAL_METADATA: dict = {
    "clinical_data": {
        "records": [
            {
                "object_url": TEST_CLINICAL_FILE_URL,
                "number_of_participants": 5,
            },
            {
                "object_url": TEST_CLINICAL_FILE_URL.replace(".", "2."),
                "number_of_participants": 3,
            },
        ],
    },
    "participants": [
        {
            "cimac_participant_id": "CTTTPP1",
            "samples": [
                {"cimac_id": "CTTTPP101.00"},
                {"cimac_id": "CTTTPP102.00"},
            ],
        },
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
                {"cimac_id": "CTTTPP302.00"},
                {"cimac_id": "CTTTPP303.00"},
            ],
        },
    ],
    "shipments": [
        {"manifest_id": TEST_MANIFEST_ID},
        {"manifest_id": TEST_MANIFEST_ID + "2"},
    ],
}
CLIPPED_METADATA_SHIPMENTS: dict = {
    "clinical_data": TRIAL_METADATA["clinical_data"],
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
    "clinical_data": {
        "records": [
            {
                "object_url": TEST_CLINICAL_FILE_URL.replace(".", "2."),
                "number_of_participants": 3,
            },
        ],
    },
    "participants": TRIAL_METADATA["participants"],
    "shipments": TRIAL_METADATA["shipments"],
}
CLIPPED_METADATA_ALL_CLINICAL: dict = {
    "participants": TRIAL_METADATA["participants"],
    "shipments": TRIAL_METADATA["shipments"],
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
    mock_files[0].object_url = f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_FILE_URL}"
    mock_files[
        1
    ].object_url = (
        f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_FILE_URL.replace('.', '2.')}"
    )

    # mock query for individual file
    query = MagicMock()
    query_filter = MagicMock()
    query_filter.all.return_value = [mock_files[0]]
    query.filter.return_value = query_filter

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
    mock_trial.metadata_json = TRIAL_METADATA
    mock_trial._updated = datetime.fromisoformat("2020-01-01T12:34:45")
    get_trial_if_exists.first.return_value = mock_trial
    monkeypatch.setattr(dbedit_remove, "get_trial_if_exists", get_trial_if_exists)

    # convenience function
    def reset_mocks():
        Session.reset_mock()
        session.reset_mock()
        begin.reset_mock()
        query.reset_mock()
        query_filter.reset_mock()
        get_clinical_downloadable_files.reset_mock()
        [mock.reset_mock() for mock in mock_files]
        get_trial_if_exists.reset_mock()
        mock_trial.reset_mock()

    # test for proper removal of single file
    reset_mocks()
    dbedit_remove.remove_clinical(TEST_TRIAL_ID, TEST_CLINICAL_FILE_URL)

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    begin.__exit__.assert_called_once()
    get_trial_if_exists.assert_called_once_with(
        TEST_TRIAL_ID, with_for_update=True, session=session
    )
    get_clinical_downloadable_files.assert_not_called()
    session.query.assert_called_once_with(DownloadableFiles)
    query.filter.assert_called_once_with(
        DownloadableFiles.trial_id == TEST_TRIAL_ID,
        DownloadableFiles.object_url
        == f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_FILE_URL}",
    )
    query_filter.all.assert_called_once_with()

    session.add.assert_called_once()
    args = session.add.call_args_list[0].args
    assert len(args) == 1

    assert isinstance(args[0]._updated, datetime)
    assert args[0]._updated != datetime.fromisoformat("2020-01-01T12:34:45")
    args[0].metadata_json == CLIPPED_METADATA_TARGET_CLINICAL

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
    session.query.assert_not_called()
    get_clinical_downloadable_files.assert_called_once_with(
        TEST_TRIAL_ID,
        session=session,
    )

    session.add.assert_called_once()
    args = session.add.call_args_list[0].args
    assert len(args) == 1

    assert isinstance(args[0]._updated, datetime)
    assert args[0]._updated != datetime.fromisoformat("2020-01-01T12:34:45")
    args[0].metadata_json == CLIPPED_METADATA_TARGET_CLINICAL

    assert session.delete.call_count == 2
    session.delete.assert_has_calls(
        [
            call(mock_files[0]),
            call(mock_files[1]),
        ]
    )

    # check that it exits if no matching file found
    reset_mocks()
    query_filter.all.return_value = []
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_clinical(
            trial_id=TEST_TRIAL_ID,
            target_id=TEST_CLINICAL_FILE_URL,
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
        metadata_json=TRIAL_METADATA,
        samples_to_remove=samples_to_remove,
    )

    # this doesn't remove the shipment itself
    clip_just_samples = deepcopy(CLIPPED_METADATA_SHIPMENTS)
    clip_just_samples["shipments"] = TRIAL_METADATA["shipments"]
    assert res == clip_just_samples


def test_remove_shipment(monkeypatch):
    # mock the session itself
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

    # mock getting the trial
    get_trial_if_exists = MagicMock()
    mock_trial = MagicMock()
    mock_trial.metadata_json = TRIAL_METADATA
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

    session.add.assert_called_once()
    args = session.add.call_args_list[0].args
    print(list(args))
    assert len(args) == 1

    assert isinstance(args[0]._updated, datetime)
    assert args[0]._updated != datetime.fromisoformat("2020-01-01T12:34:45")
    args[0].metadata_json == CLIPPED_METADATA_SHIPMENTS

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
