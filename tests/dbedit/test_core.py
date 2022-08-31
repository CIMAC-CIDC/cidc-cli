import pytest
from unittest.mock import MagicMock

from cli.dbedit import core
from cli.config import set_env

from .constants import TEST_PASSWORD, TEST_TRIAL_ID, TEST_USER


class Mocker:
    def __init__(self, monkeypatch) -> None:
        self.sqlalchemy = MagicMock()

        self.Connector = MagicMock()
        self.Connector_instance = MagicMock()
        self.Connector.return_value = self.Connector_instance

        self.sessionmaker = MagicMock()
        self.Session = MagicMock()
        self.sessionmaker.return_value = self.Session

        self.automap_base = MagicMock()
        self.Base = MagicMock()

        self.DownloadableFiles = MagicMock()
        self.TrialMetadata = MagicMock()
        self.UploadJobs = MagicMock()
        self.Users = MagicMock()

        self.Base.classes.downloadable_files = self.DownloadableFiles
        self.Base.classes.trial_metadata = self.TrialMetadata
        self.Base.classes.upload_jobs = self.UploadJobs
        self.Base.classes.users = self.Users
        self.automap_base.return_value = self.Base

        self.create_engine_result = MagicMock()

        def create_engine(*args, creator: callable, **kwargs) -> MagicMock:
            creator()
            return self.create_engine_result

        self.sqlalchemy.create_engine = MagicMock(wraps=create_engine)

        monkeypatch.setattr(core, "Connector", self.Connector)
        monkeypatch.setattr(core, "sqlalchemy", self.sqlalchemy)
        monkeypatch.setattr(core, "automap_base", self.automap_base)
        monkeypatch.setattr(core, "sessionmaker", self.sessionmaker)

        monkeypatch.setattr("builtins.input", lambda _: TEST_USER)
        monkeypatch.setattr(core.getpass, "getpass", lambda: TEST_PASSWORD)

    def reset_mocks(self):
        self.Connector.reset_mock()
        self.sqlalchemy.reset_mock()
        self.sqlalchemy.create_engine.reset_mock()
        self.automap_base.reset_mock()
        self.sessionmaker.reset_mock()


def test_connect(monkeypatch):
    monkeypatch.setattr(core, "get_env", lambda: "prod")
    monkeypatch.setattr(core, "get_username", lambda: TEST_USER)
    mocks = Mocker(monkeypatch)

    assert core.DownloadableFiles is None
    assert core.Session is None
    assert core.TrialMetadata is None
    assert core.UploadJobs is None
    assert core.Users is None

    list_mod = MagicMock()
    core.connect(list_mod)

    mocks.Connector.assert_called_once_with()
    mocks.automap_base.assert_called_once_with()
    mocks.sqlalchemy.create_engine.assert_called_once()
    args, _ = mocks.sqlalchemy.create_engine.call_args
    assert args == ("postgresql+pg8000://",)

    mocks.Connector_instance.connect.assert_called_once_with(
        "cidc-dfci:us-east1:cidc-postgresql-prod",
        "pg8000",
        user=TEST_USER,
        password=TEST_PASSWORD,
        db="cidc-prod",
    )

    mocks.sessionmaker.assert_called_once_with(mocks.create_engine_result)
    mocks.Base.prepare.assert_called_once()
    args, _ = mocks.Base.prepare.call_args
    assert args == (mocks.create_engine_result,)

    assert core.DownloadableFiles is not None
    assert core.Session is not None
    assert core.TrialMetadata is not None
    assert core.UploadJobs is not None
    assert core.Users is not None

    assert list_mod.DownloadableFiles is not None
    assert list_mod.Session is not None
    assert list_mod.TrialMetadata is not None
    assert list_mod.UploadJobs is not None
    assert list_mod.Users is not None

    mocks.reset_mocks()
    list_mod.reset_mock()
    # check that it switches to staging if no ENV
    monkeypatch.setattr(core, "get_env", lambda: None)
    core.connect(list_mod)
    mocks.Connector_instance.connect.assert_called_once_with(
        "cidc-dfci-staging:us-central1:cidc-postgresql-staging",
        "pg8000",
        user=TEST_USER,
        password=TEST_PASSWORD,
        db="cidc-staging",
    )
    mocks.reset_mocks()
    list_mod.reset_mock()
    # check that it switches to staging if weird ENV
    monkeypatch.setattr(core, "get_env", lambda: "foo")
    core.connect(list_mod)
    mocks.Connector_instance.connect.assert_called_once_with(
        "cidc-dfci-staging:us-central1:cidc-postgresql-staging",
        "pg8000",
        user=TEST_USER,
        password=TEST_PASSWORD,
        db="cidc-staging",
    )


def test_get_clinical_downloadable_files(monkeypatch):
    monkeypatch.setattr(core, "get_env", lambda: "dev")
    DownloadableFiles = MagicMock()
    monkeypatch.setattr(core, "DownloadableFiles", DownloadableFiles)

    session = MagicMock()
    # these are to hold the results
    query = MagicMock()
    query_filter = MagicMock()

    mock_files = [MagicMock(), MagicMock()]
    query_filter.all.return_value = mock_files

    query.filter.return_value = query_filter
    session.query.return_value = query

    res: list = core.get_clinical_downloadable_files(TEST_TRIAL_ID, session=session)
    assert len(res) == 2 and res is mock_files

    session.query.assert_called_once_with(DownloadableFiles)
    query.filter.assert_called_once_with(
        DownloadableFiles.trial_id == TEST_TRIAL_ID,
        DownloadableFiles.object_url.like("%/clinical/%"),
    )
    query_filter.all.assert_called_once_with()


def test_get_misc_data_files(monkeypatch):
    monkeypatch.setattr(core, "get_env", lambda: "dev")
    DownloadableFiles = MagicMock()
    monkeypatch.setattr(core, "DownloadableFiles", DownloadableFiles)

    session = MagicMock()
    # these are to hold the results
    query = MagicMock()
    query_filter = MagicMock()

    mock_files = [MagicMock(), MagicMock()]
    query_filter.all.return_value = mock_files

    query.filter.return_value = query_filter
    session.query.return_value = query

    res: list = core.get_misc_data_files(TEST_TRIAL_ID, session=session)
    assert len(res) == 2 and res is mock_files

    session.query.assert_called_once_with(DownloadableFiles)
    query.filter.assert_called_once_with(
        DownloadableFiles.trial_id == TEST_TRIAL_ID,
        DownloadableFiles.object_url.like("%/misc_data/%"),
    )
    query_filter.all.assert_called_once_with()


def test_get_shipments(monkeypatch):
    monkeypatch.setattr(core, "get_env", lambda: "dev")
    UploadJobs = MagicMock()
    monkeypatch.setattr(core, "UploadJobs", UploadJobs)

    session = MagicMock()
    # these are to hold the results
    query = MagicMock()
    query_filter = MagicMock()

    mock_uploads = [MagicMock(), MagicMock()]
    mock_uploads[0].metadata_patch = {"shipments": []}  # should be returned
    mock_uploads[1].metadata_patch = {}  # should NOT be returned
    query_filter.all.return_value = mock_uploads

    query.filter.return_value = query_filter
    session.query.return_value = query

    res: list = core.get_shipments(TEST_TRIAL_ID, session=session)
    assert len(res) == 1 and res[0] is mock_uploads[0]

    session.query.assert_called_once_with(UploadJobs)
    query.filter.assert_called_once_with(
        UploadJobs.trial_id == TEST_TRIAL_ID,
        UploadJobs.status == "merge-completed",
    )
    query_filter.all.assert_called_once_with()


def test_get_trial_if_exists(monkeypatch):
    monkeypatch.setattr(core, "get_env", lambda: "dev")
    Session = MagicMock()
    session = MagicMock()
    begin = MagicMock()

    TrialMetadata = MagicMock()
    monkeypatch.setattr(core, "TrialMetadata", TrialMetadata)

    # these are to hold the results
    query = MagicMock()
    query_filter = MagicMock()
    with_for_update = MagicMock()

    mock_trial = MagicMock()
    mock_trial.metadata_json = {"foo": "bar"}

    with_for_update.first.return_value = mock_trial
    query_filter.with_for_update.return_value = with_for_update
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(core, "Session", Session)

    def reset_mocks():
        Session.reset_mock()
        session.reset_mock()
        begin.reset_mock()
        TrialMetadata.reset_mock()
        query.reset_mock()
        query_filter.reset_mock()
        with_for_update.reset_mock()
        mock_trial.reset_mock()

    # check it returns the trial for update
    with_for_update.first.return_value = mock_trial
    query_filter.with_for_update.return_value = with_for_update
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(core, "Session", Session)

    reset_mocks()
    trial: TrialMetadata = core.get_trial_if_exists(
        trial_id=TEST_TRIAL_ID,
        with_for_update=True,
        session=session,
    )
    assert trial is mock_trial

    # check that it exits if trial not found for update
    with_for_update.first.return_value = None
    query_filter.with_for_update.return_value = with_for_update
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(core, "Session", Session)

    reset_mocks()
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        core.get_trial_if_exists(
            trial_id=TEST_TRIAL_ID,
            with_for_update=True,
            session=session,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

    # check it returns the trial NOT for update
    query_filter.first.return_value = mock_trial
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(core, "Session", Session)

    reset_mocks()
    trial: TrialMetadata = core.get_trial_if_exists(
        trial_id=TEST_TRIAL_ID,
        session=session,
    )
    assert trial is mock_trial

    # check that it exits if trial not found NOT for update
    query_filter.first.return_value = None
    query.filter.return_value = query_filter
    session.query.return_value = query
    begin.__enter__.return_value = session
    Session.begin.return_value = begin
    monkeypatch.setattr(core, "Session", Session)

    reset_mocks()
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        core.get_trial_if_exists(
            trial_id=TEST_TRIAL_ID,
            session=session,
        )
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
