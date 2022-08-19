from datetime import datetime
from typing import Dict, List

from .core import get_shipments, Session, TrialMetadata, UploadJobs


def _remove_samples_from_blob(
    metadata_json: dict,
    samples_to_delete: Dict[str, List[str]],
) -> dict:
    """
    Removes a participant completely if removing all of its samples

    Parameters
    ----------
    metadata_json: dict
        the full clinical trial metadata blob
    samples_to_delete: Dict[str, List[str]]
        map from `cimac_participant_id`s to a list of `cimac_id`s to remove
    """
    n: int = 0
    while n < len(metadata_json["participants"]):
        partic = metadata_json["participants"][n]
        cimac_partic_id = partic["cimac_participant_id"]
        if cimac_partic_id in samples_to_delete:
            if len(partic["samples"]) == len(samples_to_delete[cimac_partic_id]):
                metadata_json["participants"].pop(n)
                # don't increment because we popped
                continue

            else:
                to_delete = samples_to_delete[cimac_partic_id]
                metadata_json["participants"][n]["samples"] = [
                    s for s in partic["samples"] if s["cimac_id"] not in to_delete
                ]
        n += 1

    return metadata_json


def remove_shipment(trial_id: str, target_id: str, *, session: Session):
    with Session.begin() as session:
        trial: TrialMetadata = (
            session.query(TrialMetadata)
            .filter(TrialMetadata.trial_id == trial_id)
            .with_for_update()
            .first()
        )
        if not trial:
            print(f"Trial {trial_id} cannot be found")
            exit()

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
        samples_to_delete = {
            partic["cimac_participant_id"]: [
                sample["cimac_id"] for sample in partic["samples"]
            ]
            for upload in targets
            for partic in upload.metadata_patch.get("participants", [])
        }
        if not len(samples_to_delete):
            print(f"Shipment {target_id} for trial {trial_id} has no samples")
            exit()

        # remove the samples
        trial.metadata_json = _remove_samples_from_blob(
            metadata_json=trial.metadata_json,
            samples_to_delete=samples_to_delete,
        )
        # remove the shipment
        trial.metadata_json["shipments"] = [
            s for s in trial.metadata_json["shipments"] if s["manifest_id"] != target_id
        ]

        # update the `trial_metadata`
        trial._updated = datetime.now()
        session.add(trial)

        # remove the `upload_job`s
        for t in targets:
            session.delete(t)
