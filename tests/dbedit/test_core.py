from unittest.mock import MagicMock

from cli.dbedit import core

TEST_PASSWORD: str = "password"
TEST_TRIAL_ID: str = "test_prism_trial_id"
TEST_USER: str = "test_user"


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
    mocks = Mocker(monkeypatch)

    assert core.DownloadableFiles is None
    assert core.Session is None
    assert core.TrialMetadata is None
    assert core.UploadJobs is None
    assert core.Users is None

    core.connect()

    mocks.Connector.assert_called_once_with()
    mocks.automap_base.assert_called_once_with()
    mocks.sqlalchemy.create_engine.assert_called_once()
    assert mocks.sqlalchemy.create_engine.call_args_list[0].args == (
        "postgresql+pg8000://",
    )

    mocks.Connector_instance.connect.assert_called_once_with(
        "cidc-dfci:us-east1:cidc-postgresql-prod",
        "pg8000",
        user=TEST_USER,
        password=TEST_PASSWORD,
        db="cidc-prod",
    )

    mocks.sessionmaker.assert_called_once_with(mocks.create_engine_result)
    mocks.Base.prepare.assert_called_once()
    assert mocks.Base.prepare.call_args_list[0].args == (mocks.create_engine_result,)

    assert core.DownloadableFiles is not None
    assert core.Session is not None
    assert core.TrialMetadata is not None
    assert core.UploadJobs is not None
    assert core.Users is not None

    mocks.reset_mocks()
    # check that it switches to staging if no ENV
    monkeypatch.setattr(core, "get_env", lambda: None)
    core.connect()
    mocks.Connector_instance.connect.assert_called_once_with(
        "cidc-dfci-staging:us-central1:cidc-postgresql-staging",
        "pg8000",
        user=TEST_USER,
        password=TEST_PASSWORD,
        db="cidc-staging",
    )
    mocks.reset_mocks()
    # check that it switches to staging if weird ENV
    monkeypatch.setattr(core, "get_env", lambda: "foo")
    core.connect()
    mocks.Connector_instance.connect.assert_called_once_with(
        "cidc-dfci-staging:us-central1:cidc-postgresql-staging",
        "pg8000",
        user=TEST_USER,
        password=TEST_PASSWORD,
        db="cidc-staging",
    )


def test_get_shipments(monkeypatch):
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
