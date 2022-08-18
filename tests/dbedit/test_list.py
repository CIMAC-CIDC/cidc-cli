from datetime import datetime
import pandas as pd
from unittest.mock import MagicMock

from cli.dbedit import list as dbedit_list

TEST_TRIAL_ID: str = "test_prism_trial_id"


def test_list_shipments(monkeypatch):
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()
    begin.__enter__.return_value = session
    Session.begin.return_value = begin

    monkeypatch.setattr(dbedit_list, "Session", Session)

    upload1 = MagicMock()
    upload1.upload_type = "pbmc"
    upload1.metadata_patch = {
        "participants": [
            {"samples": [None] * 3},
            {"samples": [None]},
        ],
        "shipments": [{"manifest_id": "test_upload"}],
    }
    upload1._created = datetime.fromisoformat("2020-01-01T12:34:45")

    upload2 = MagicMock()
    upload2.upload_type = "plasma"
    upload2.metadata_patch = {
        "participants": [
            {"samples": [None] * 3},
            {"samples": [None] * 2},
        ],
        "shipments": [{"manifest_id": "test_upload2"}],
    }
    upload2._created = datetime.fromisoformat("2020-02-02T12:34:45")

    get_shipments = MagicMock()
    get_shipments.return_value = [upload1, upload2]
    monkeypatch.setattr(dbedit_list, "get_shipments", get_shipments)

    mock_print = MagicMock()
    monkeypatch.setattr("builtins.print", mock_print)

    dbedit_list.list_shipments(TEST_TRIAL_ID)

    Session.begin.assert_called_once_with()
    begin.__enter__.assert_called_once()
    get_shipments.assert_called_once_with(TEST_TRIAL_ID, session=session)
    begin.__exit__.assert_called_once()

    mock_print.assert_called_once()
    args = mock_print.call_args_list[0].args
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
