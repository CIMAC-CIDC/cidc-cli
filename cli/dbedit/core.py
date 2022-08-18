import getpass
from typing import List, Optional
import warnings

from google.cloud.sql.connector import Connector
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from .. import cache
from ..config import get_env

global Session
global DownloadableFiles, TrialMetadata, UploadJobs, Users

Session = None
DownloadableFiles, TrialMetadata, UploadJobs, Users = None, None, None, None


def connect():
    ENV: str = get_env()
    if ENV not in ["prod", "staging"]:
        print("unknown ENV, applying to staging:", ENV)
        ENV: str = "staging"

    username: Optional[str] = cache.get("username")
    if not username:
        username = input("Username: ")
        cache.store("username", username)

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


def get_shipments(trial_id: str, *, session: Session) -> List[UploadJobs]:
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
