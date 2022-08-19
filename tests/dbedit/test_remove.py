from copy import deepcopy
from datetime import datetime
import pytest
from typing import Dict, List
from unittest.mock import MagicMock, PropertyMock

from cli.dbedit import remove as dbedit_remove

TEST_MANIFEST_ID: str = "test_upload"
TEST_TRIAL_ID: str = "test_prism_trial_id"

TRIAL_METADATA: dict = {
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
CLIPPED_METADATA: dict = {
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


def test_remove_samples_from_blob():
    samples_to_delete: Dict[str, List[str]] = {
        "CTTTPP1": ["CTTTPP101.00"],
        "CTTTPP2": ["CTTTPP201.00", "CTTTPP202.00"],
        "CTTTPP3": ["CTTTPP302.00"],
    }

    res = dbedit_remove._remove_samples_from_blob(
        metadata_json=TRIAL_METADATA,
        samples_to_delete=samples_to_delete,
    )

    # this doesn't remove the shipment itself
    clip_just_samples = deepcopy(CLIPPED_METADATA)
    clip_just_samples["shipments"] = TRIAL_METADATA["shipments"]
    assert res == clip_just_samples


def test_remove_shipment(monkeypatch):
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()

    TrialMetadata = MagicMock()
    UploadJobs = MagicMock()
    monkeypatch.setattr(dbedit_remove, "TrialMetadata", TrialMetadata)
    monkeypatch.setattr(dbedit_remove, "UploadJobs", UploadJobs)

    # these are to hold the results
    query = MagicMock()
    query_filter = MagicMock()
    with_for_update = MagicMock()

    mock_trial = MagicMock()
    mock_trial.metadata_json = TRIAL_METADATA
    mock_trial._updated = datetime.fromisoformat("2020-01-01T12:34:45")

    with_for_update.first.return_value = mock_trial
    query_filter.with_for_update.return_value = with_for_update
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

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

    def reset_mocks():
        Session.reset_mock()
        session.reset_mock()
        begin.reset_mock()
        TrialMetadata.reset_mock()
        UploadJobs.reset_mock()
        query.reset_mock()
        query_filter.reset_mock()
        with_for_update.reset_mock()
        mock_trial.reset_mock()
        [mock.reset_mock() for mock in mock_uploads]
        get_shipments.reset_mock()

    dbedit_remove.remove_shipment(
        trial_id=TEST_TRIAL_ID,
        target_id=TEST_MANIFEST_ID,
        session=session,
    )

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    begin.__exit__.assert_called_once()

    session.query.assert_called_once_with(TrialMetadata)
    query.filter.assert_called_once_with(
        TrialMetadata.trial_id == TEST_TRIAL_ID,
    )
    query_filter.with_for_update.assert_called_once_with()
    with_for_update.first.assert_called_once_with()
    get_shipments.assert_called_once_with(TEST_TRIAL_ID, session=session)

    session.add.assert_called_once()
    args = session.add.call_args_list[0].args
    assert len(args) == 1

    assert isinstance(mock_trial._updated, datetime)
    assert mock_trial._updated != datetime.fromisoformat("2020-01-01T12:34:45")
    mock_trial.metadata_json == CLIPPED_METADATA

    assert session.delete.call_count == 2
    assert [call.args for call in session.delete.call_args_list] == [
        (mock_uploads[0],),
        (mock_uploads[2],),
    ]

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
            session=session,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    remove_samples_from_blob.assert_not_called()

    # check that it exits if no matching manifest found
    reset_mocks()
    remove_samples_from_blob.reset_mock()
    get_shipments.return_value = []
    monkeypatch.setattr(dbedit_remove, "get_shipments", get_shipments)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_shipment(
            trial_id=TEST_TRIAL_ID,
            target_id=TEST_MANIFEST_ID,
            session=session,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    remove_samples_from_blob.assert_not_called()

    # check that it exits if trial not found
    reset_mocks()
    with_for_update.first.return_value = None
    query_filter.with_for_update.return_value = with_for_update
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(dbedit_remove, "Session", Session)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dbedit_remove.remove_shipment(
            trial_id=TEST_TRIAL_ID,
            target_id=TEST_MANIFEST_ID,
            session=session,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    get_shipments.assert_not_called()
