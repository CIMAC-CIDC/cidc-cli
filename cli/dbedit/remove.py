from datetime import datetime
from typing import Dict, List

from .core import (
    DownloadableFiles,
    get_clinical_downloadable_files,
    get_shipments,
    get_trial_if_exists,
    Session,
    TrialMetadata,
    UploadJobs,
)


def remove_clinical(trial_id: str, target_id: str, *, session: Session):
    """
    Removes a clinical file completely, include its downloadle_files entry

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    target_id: str
        the object_url of the file to remove
        not including {trial_id}/clinical/
        special value * for all files for this trial
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(
            trial_id, with_for_update=True, session=session
        )

        if target_id == "*":
            # get all of the clinical files
            targets: List[DownloadableFiles] = get_clinical_downloadable_files(
                trial_id, session=session
            )
        else:
            # get just the one(s) we're looking for
            targets: List[DownloadableFiles] = (
                session.query(DownloadableFiles)
                .filter(
                    DownloadableFiles.trial_id == trial_id,
                    DownloadableFiles.object_url == f"{trial_id}/clinical/{target_id}",
                )
                .all()
            )
        target_urls = [f.object_url for f in targets]

        if not len(targets):
            if target_id == "*":
                print(f"No clinical data files found for trial {trial_id}")
            else:
                print(f"Clinical data file {target_id} not found for trial {trial_id}")
            exit()

        # remove the file(s)
        trial.metadata_json["clinica_data"] = [
            r
            for r in trial.metadata_json.get("clinical_data", {}).get("records", [])
            if r["clinical_file"]["object_url"] not in target_urls
        ]

        # update the `trial_metadata`
        trial._updated = datetime.now()
        session.add(trial)

        # remove the `downloadable_files`
        for t in targets:
            session.delete(t)


def _remove_samples_from_blob(
    metadata_json: dict,
    samples_to_remove: Dict[str, List[str]],
) -> dict:
    """
    Removes a participant completely if removing all of its samples

    Parameters
    ----------
    metadata_json: dict
        the full clinical trial metadata blob
    samples_to_remove: Dict[str, List[str]]
        map from `cimac_participant_id`s to a list of `cimac_id`s to remove
    """
    n: int = 0
    while n < len(metadata_json["participants"]):
        partic = metadata_json["participants"][n]
        cimac_partic_id = partic["cimac_participant_id"]
        if cimac_partic_id in samples_to_remove:
            if len(partic["samples"]) == len(samples_to_remove[cimac_partic_id]):
                metadata_json["participants"].pop(n)
                # don't increment because we popped
                continue

            else:
                to_remove = samples_to_remove[cimac_partic_id]
                metadata_json["participants"][n]["samples"] = [
                    s for s in partic["samples"] if s["cimac_id"] not in to_remove
                ]
        n += 1

    return metadata_json


def remove_shipment(trial_id: str, target_id: str, *, session: Session):
    """
    Removes a shipment completely with all of its samples, including its upload_jobs entry
    Removes a participant completely if removing all of its samples

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    target_id: str
        the manifest_id of the shipment to remove
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(
            trial_id, with_for_update=True, session=session
        )

        # get all of the shipments
        shipments: List[UploadJobs] = get_shipments(trial_id, session=session)
        # find the one(s) we're looking for
        targets = [
            s
            for s in shipments
            if s.metadata_patch["shipments"][0]["manifest_id"] == target_id
        ]

        if not len(targets):
            print(f"Shipment {target_id} not found for trial {trial_id}")
            exit()

        # get all the associated samples
        samples_to_remove = {
            partic["cimac_participant_id"]: [
                sample["cimac_id"] for sample in partic["samples"]
            ]
            for upload in targets
            for partic in upload.metadata_patch.get("participants", [])
        }
        if not len(samples_to_remove):
            print(f"Shipment {target_id} for trial {trial_id} has no samples")
            exit()

        # remove the samples
        trial.metadata_json = _remove_samples_from_blob(
            metadata_json=trial.metadata_json,
            samples_to_remove=samples_to_remove,
        )
        # remove the shipment(s)
        trial.metadata_json["shipments"] = [
            s for s in trial.metadata_json["shipments"] if s["manifest_id"] != target_id
        ]

        # update the `trial_metadata`
        trial._updated = datetime.now()
        session.add(trial)

        # remove the `upload_jobs`
        for t in targets:
            session.delete(t)
