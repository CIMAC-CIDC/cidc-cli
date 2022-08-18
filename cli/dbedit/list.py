import pandas as pd
from typing import List

from .core import get_shipments, Session, UploadJobs


def list_shipments(trial_id: str):
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
