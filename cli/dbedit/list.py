import pandas as pd
from typing import Dict, List

from .core import (
    DownloadableFiles,
    get_clinical_downloadable_files,
    get_trial_if_exists,
    get_shipments,
    Session,
    TrialMetadata,
    UploadJobs,
)


def list_clinical(trial_id: str):
    """
    Prints a table describing all clinical files for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(trial_id, session=session)
        clinical_files: List[DownloadableFiles] = get_clinical_downloadable_files(
            trial_id, session=session
        )

        number_of_participants: Dict[str, dict] = {
            record["clinical_file"]["object_url"]: record["clinical_file"][
                "number_of_participants"
            ]
            for record in trial.metadata_json.get("clinical_data", {}).get(
                "records", []
            )
        }

        print(
            pd.DataFrame(
                {
                    "object_url": f.object_url,
                    "filename": f.object_url.split("/clinical/")[1],
                    "num_participants": number_of_participants.get(f.object_url, pd.NA),
                    "created": f._created,
                }
                for f in clinical_files
            )
        )


def list_shipments(trial_id: str):
    """
    Prints a table describing all shipments for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    """
    with Session.begin() as session:
        shipments: List[UploadJobs] = get_shipments(trial_id, session=session)
        print(
            pd.DataFrame(
                {
                    "upload_type": u.upload_type,
                    "manifest_id": u.metadata_patch["shipments"][0]["manifest_id"],
                    "num_samples": sum(
                        len(p["samples"]) for p in u.metadata_patch["participants"]
                    ),
                    "created": u._created,
                }
                for u in shipments
            )
        )
