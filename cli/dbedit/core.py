import getpass
from types import ModuleType
from typing import List, Optional
import warnings
from .config import get_username, set_username

from google.cloud.sql.connector import Connector
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from ..config import get_env

global Session
global DownloadableFiles, TrialMetadata, UploadJobs, Users

Session = None
DownloadableFiles, TrialMetadata, UploadJobs, Users = None, None, None, None


def connect(list_mod: ModuleType) -> None:
    """
    Set up this module to be able to make sqlalchemy calls
    uses ENV as set by $ cidc config set-env
    defaults to staging unless `prod` is specified ie no `dev` mode

    If not already loaded, will ask for your database username
    Asks for database password every time as to not store it
    """
    ENV: str = get_env()
    if ENV not in ["prod", "staging"]:
        print("unknown ENV, applying to staging:", ENV)
        ENV: str = "staging"

    username: Optional[str] = get_username()
    if not username:
        username = input("Username: ")
        set_username(username)

    password = getpass.getpass()
    connection_name = (
        "cidc-dfci:us-east1:cidc-postgresql-prod"
        if ENV == "prod"
        else "cidc-dfci-staging:us-central1:cidc-postgresql-staging"
    )

    # initialize Connector object
    connector = Connector()

    # function to return the database connection
    def getconn():
        conn = connector.connect(
            connection_name,
            "pg8000",
            user=username,
            password=password,
            db="cidc-" + ("prod" if ENV == "prod" else "staging"),
        )
        return conn

    Base = automap_base()
    engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)

    global Session
    Session = sessionmaker(engine)

    # from here, Base.classes will have each table as an attribute
    # they are sqlalchemy tables equivalent to the ones in API/models/models.py
    # eg Base.classes.trial_metadata works like cidc_api.models.TrialMetadata
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=sqlalchemy.exc.SAWarning)
        Base.prepare(
            engine,
            reflection_options={
                "only": ["downloadable_files", "trial_metadata", "upload_jobs", "users"]
            },
        )

    # these won't have tab complete because they're reflecting not defining
    global DownloadableFiles, TrialMetadata, UploadJobs, Users

    DownloadableFiles = Base.classes.downloadable_files
    TrialMetadata = Base.classes.trial_metadata
    UploadJobs = Base.classes.upload_jobs
    Users = Base.classes.users

    # wire up the passed module
    # this is a hack to not pass them around
    list_mod.Session = Session
    list_mod.DownloadableFiles = DownloadableFiles
    list_mod.TrialMetadata = TrialMetadata
    list_mod.UploadJobs = UploadJobs
    list_mod.Users = Users


def get_clinical_downloadable_files(
    trial_id: str, *, session: Session
) -> List[DownloadableFiles]:
    """
    Get all downloadable_files rows from clinical data files for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    session: Session
        a session created from this module's `Session` after `connect()` is called
    """
    return (
        session.query(DownloadableFiles)
        .filter(
            DownloadableFiles.trial_id == trial_id,
            DownloadableFiles.object_url.like("%/clinical/%"),
        )
        .all()
    )


def get_misc_data_files(trial_id: str, *, session: Session) -> List[DownloadableFiles]:
    """
    Get all downloadable_files rows from misc_data uploads for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    session: Session
        a session created from this module's `Session` after `connect()` is called
    """
    return (
        session.query(DownloadableFiles)
        .filter(
            DownloadableFiles.trial_id == trial_id,
            DownloadableFiles.object_url.like("%/misc_data/%"),
        )
        .all()
    )


def get_shipments(trial_id: str, *, session: Session) -> List[UploadJobs]:
    """
    Get all upload_jobs rows from successful manifest uploads for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    session: Session
        a session created from this module's `Session` after `connect()` is called
    """
    # the "shipments" in trial_metadata don't have which
    # samples they came with, so we have to check the uploads
    shipments = []
    for u in (
        session.query(UploadJobs)
        .filter(
            UploadJobs.trial_id == trial_id,
            UploadJobs.status == "merge-completed",
        )
        .all()
    ):
        # only for shipment uploads
        if "shipments" in u.metadata_patch:
            shipments.append(u)
    return shipments


def get_trial_if_exists(
    trial_id: str, *, with_for_update: bool = False, session: Session
) -> TrialMetadata:
    """
    Get the trial_metadata row for the given trial for update
    Exits with message if trial does not exist

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    session: Session
        a session created from this module's `Session` after `connect()` is called
    """
    query = session.query(TrialMetadata).filter(TrialMetadata.trial_id == trial_id)
    if with_for_update:
        query = query.with_for_update()
    trial: TrialMetadata = query.first()

    if not trial:
        print(f"Trial {trial_id} cannot be found")
        exit()

    return trial
